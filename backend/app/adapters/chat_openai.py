"""The built-in AI's tool loop on the OpenAI Responses API (spec 8, "The OpenAI path").

chat.py runs the turn: its context, its tools with their steps and cases, and the number check.
This module only talks to the API. It streams each response, passes its text on, runs the
function calls the response asks for and sends their outputs back, until the model answers, a
response fails or the round trips run out. It imports nothing from chat.py, which imports it.
"""

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import cast

import httpx2
import openai
from openai.types.responses import (
    FunctionToolParam,
    Response,
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseFunctionToolCall,
    ResponseIncompleteEvent,
    ResponseOutputItem,
    ResponseStreamEvent,
)
from openai.types.responses.response_input_param import (
    FunctionCallOutput,
    ResponseInputItemParam,
    ResponseInputParam,
)
from openai.types.shared import ReasoningEffort

from app.adapters.chat_text import (
    AI_CUT_OFF_MESSAGE,
    AI_FAILED_MESSAGE,
    AI_REFUSED_MESSAGE,
    AI_STEP_LIMIT_MESSAGE,
    PARAGRAPH_BREAK,
)

logger = logging.getLogger(__name__)

# Spec 8, "The OpenAI path": effort low, as on the Claude path.
REASONING_EFFORT: ReasoningEffort = "low"
# A function call's output carries no error flag, so a failed call says so at the start of its
# text.
FUNCTION_ERROR_PREFIX = "Error: "
# The one reason of an incomplete response that means its answer was cut off.
_CUT_OFF_REASON = "max_output_tokens"

# Runs the named tool on its arguments, given as JSON text, and returns the output the model
# gets. Raises `FunctionCallError` when the call fails.
CallTool = Callable[[str, str], Awaitable[str]]
EmitText = Callable[[str], None]

# The events that end the stream of a response.
_FinalEvent = (
    ResponseCompletedEvent | ResponseIncompleteEvent | ResponseFailedEvent | ResponseErrorEvent
)


class FunctionCallError(Exception):
    """Raised by a `CallTool` whose call failed. The model gets `message`, marked as an error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class _NoAnswer(Exception):
    """A response that gives the turn no usable answer."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(reason)
        # Logged: how the response ended, in the API's terms, never words of the conversation.
        self.reason = reason
        # Sent to the browser: the plain message of spec 8, "Failure".
        self.message = message


@dataclass
class _Answer:
    """The turn's answer text, passed on as it arrives."""

    emit_text: EmitText
    parts: list[str] = field(default_factory=list)
    _new_paragraph: bool = False

    def start_message(self) -> None:
        self._new_paragraph = bool(self.parts)

    def add(self, delta: str) -> None:
        if self._new_paragraph:
            delta = PARAGRAPH_BREAK + delta
            self._new_paragraph = False
        self.parts.append(delta)
        self.emit_text(delta)

    def text(self) -> str:
        return "".join(self.parts)


async def run_turn(
    client: openai.AsyncOpenAI,
    *,
    model: str,
    instructions: str,
    input_items: Sequence[ResponseInputItemParam],
    tools: Sequence[FunctionToolParam],
    max_output_tokens: int,
    max_iterations: int,
    call_tool: CallTool,
    emit_text: EmitText,
) -> tuple[str, str | None]:
    """One AI turn of at most `max_iterations` requests, each streamed, with the function calls
    each response asks for run in order. Returns the answer text, as passed to `emit_text`, and
    the plain message to send instead of an answer; None when the model answered.

    When the last allowed response still asks for function calls, they run, so their steps and
    cases reach the browser, and the turn then ends with AI_STEP_LIMIT_MESSAGE.
    """
    answer = _Answer(emit_text)
    turn_input: ResponseInputParam = list(input_items)
    for _ in range(max_iterations):
        try:
            stream = await client.responses.create(
                model=model,
                instructions=instructions,
                input=turn_input,
                tools=tools,
                reasoning={"effort": REASONING_EFFORT},
                max_output_tokens=max_output_tokens,
                # Spec 8: the API keeps every response for later retrieval unless told not to,
                # and the app stores no chat text. Each request sends the whole turn instead.
                store=False,
                stream=True,
            )
            response = await _read_response(stream, answer)
        except _NoAnswer as no_answer:
            logger.warning("AI turn stopped with %s", no_answer.reason)
            return answer.text(), no_answer.message
        # The SDK wraps a transport error raised while it sends a request or reads a stream, but
        # not one raised while it reads the body of an error reply, which arrives as httpx2's own.
        except (openai.APIError, httpx2.TransportError) as error:
            logger.warning("AI call failed with %s", type(error).__name__)
            return answer.text(), AI_FAILED_MESSAGE
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return answer.text(), None
        turn_input.extend(_as_input(item) for item in response.output)
        for call in calls:
            turn_input.append(await _function_call_output(call, call_tool))
    return answer.text(), AI_STEP_LIMIT_MESSAGE


async def _read_response(
    stream: openai.AsyncStream[ResponseStreamEvent], answer: _Answer
) -> Response:
    """Read one response's stream to its end, passing its text on to `answer`, and return the
    response once it completed. Raises `_NoAnswer` when the response was refused, cut off or
    failed, or its stream ended before its final event.
    """
    final: _FinalEvent | None = None
    refused = False
    async with stream:
        async for event in stream:
            if event.type == "response.output_item.added" and event.item.type == "message":
                answer.start_message()
            elif event.type == "response.output_text.delta":
                answer.add(event.delta)
            elif event.type == "response.refusal.delta":
                refused = True
            elif isinstance(event, _FinalEvent):
                final = event
    if refused:
        raise _NoAnswer("refusal", AI_REFUSED_MESSAGE)
    return _completed_response(final)


def _completed_response(final: _FinalEvent | None) -> Response:
    """The response that `final` ended, when it completed. Spec 8, "Failure": a cut-off answer,
    an incomplete or failed response, an error event and a stream without a final event give no
    answer, so they raise `_NoAnswer`. So does a refusal written as a message part.
    """
    if final is None:
        raise _NoAnswer("no final event", AI_FAILED_MESSAGE)
    if final.type == "error":
        raise _NoAnswer("error", AI_FAILED_MESSAGE)
    if final.type == "response.failed":
        raise _NoAnswer("failed", AI_FAILED_MESSAGE)
    if final.type == "response.incomplete":
        details = final.response.incomplete_details
        reason = details.reason if details is not None else None
        message = AI_CUT_OFF_MESSAGE if reason == _CUT_OFF_REASON else AI_FAILED_MESSAGE
        raise _NoAnswer(reason or "incomplete", message)
    if _has_refusal(final.response):
        raise _NoAnswer("refusal", AI_REFUSED_MESSAGE)
    return final.response


def _has_refusal(response: Response) -> bool:
    return any(
        part.type == "refusal"
        for item in response.output
        if item.type == "message"
        for part in item.content
    )


def _as_input(item: ResponseOutputItem) -> ResponseInputItemParam:
    """An output item as the next request's input, unchanged: reasoning items keep their
    encrypted content, which the API needs because it stores nothing. A function call's id may
    be null in output but not in input, so a null id is left out, as the SDK's own Responses
    tool runner does.
    """
    data = item.to_dict()
    if data.get("id") is None:
        data.pop("id", None)
    return cast(ResponseInputItemParam, data)


async def _function_call_output(
    call: ResponseFunctionToolCall, call_tool: CallTool
) -> FunctionCallOutput:
    try:
        output = await call_tool(call.name, call.arguments)
    except FunctionCallError as error:
        output = FUNCTION_ERROR_PREFIX + error.message
    return {"type": "function_call_output", "call_id": call.call_id, "output": output}
