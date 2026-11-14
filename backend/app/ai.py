"""Shared bounds and provider calls for the AI paths of spec 8.

The planner, discovery and explanation adapters all use these: a bounded request body, one
generation at a time across workers, per-address and daily limits, conservative budget
reservations made before every paid call, and single OpenAI calls without retries.
"""

import hashlib
import json
import math
import re
import time
import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import Request
from pydantic import ValidationError

from app.config import VECTOR_STORE_ID_PATTERN
from app.errors import AiUnavailableError, BadRequestError, RateLimitedError
from app.models import (
    MAX_PASSAGES,
    PASSAGE_MAX_LENGTH,
    Citation,
    DocumentSource,
    RetrievedPassage,
    UnansweredReason,
)
from app.services import Services

# Spec 8, "Bounds and evaluation": every AI request body is at most 8 KiB, and the whole
# provider operation has a 30-second deadline.
MAX_BODY_BYTES = 8192
DEADLINE_SECONDS = 30
# The operations lease outlives the deadline a little, so a slow release never lets a second
# generation start while the first is still finishing.
LEASE_GRACE_SECONDS = 5
GENERATION_LEASE = "generation"
# One daily counter for every AI path, so AI_DAILY_TURNS caps all of them together. The name
# predates discovery and explanation; renaming it would reset the day's count.
AI_TURNS_COUNTER = "planner_turns"
# Bytes conservatively bound input text tokens; this allowance covers message framing.
MESSAGE_FRAMING_TOKENS = 1024
MICROUSD_PER_MILLION = 1_000_000

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_VECTOR_STORES_URL = "https://api.openai.com/v1/vector_stores"
# A sentence end in the last half of a capped passage is a good place to cut it.
_SENTENCE_END = re.compile(r"[.!?](?=\s)")

ProviderFailure = Literal["refused", "incomplete", "empty"]
# Spec 5: the contract reason of each provider failure. An output with no text is as unusable
# as one cut short, so both count as incomplete.
_FAILURE_REASONS: dict[ProviderFailure, UnansweredReason] = {
    "refused": "provider_refused",
    "incomplete": "provider_incomplete",
    "empty": "provider_incomplete",
}


class ProviderOutputError(ValueError):
    """The provider answered, but with a refusal, an incomplete output or no text (spec 5)."""

    def __init__(self, reason: ProviderFailure) -> None:
        super().__init__(f"The provider output was {reason}.")
        self.reason = reason

    @property
    def unanswered_reason(self) -> UnansweredReason:
        """The `reason` a discovery or explanation response reports for this failure."""
        return _FAILURE_REASONS[self.reason]


async def read_bounded_body(request: Request, too_large_message: str) -> bytes:
    """The request body, read in chunks; raises `BadRequestError` past `MAX_BODY_BYTES`.

    Reading stops at the first chunk over the bound, so a huge body is never held in memory.
    """
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise BadRequestError(too_large_message)
    return bytes(body)


@asynccontextmanager
async def generation_slot(request: Request, services: Services) -> AsyncIterator[None]:
    """Hold the one AI generation slot for the body of the `async with` block (spec 8).

    Raises `RateLimitedError` when this worker or another worker sharing the operations
    database is already generating, when the address is over its per-minute limit, or when
    the daily AI turn limit is reached. The slot is released however the block ends.
    """
    if services.planner_busy:
        raise RateLimitedError(
            "One AI generation is already running; try manual controls or retry shortly."
        )
    services.planner_busy = True
    token = uuid.uuid4().hex
    leased = False
    try:
        if not services.planner_limiter.allow(request.client.host if request.client else "unknown"):
            raise RateLimitedError("Too many AI requests from this address.")
        if services.operations is not None:
            leased = services.operations.acquire_lease(
                GENERATION_LEASE, token, time.time(), DEADLINE_SECONDS + LEASE_GRACE_SECONDS
            )
            if not leased:
                raise RateLimitedError("Another AI generation is running.")
            count = services.operations.increment_counter(
                AI_TURNS_COUNTER, services.today().isoformat()
            )
            if count > services.settings.ai_daily_turns:
                raise RateLimitedError("The daily AI request limit has been reached.")
        yield
    finally:
        if leased and services.operations is not None:
            services.operations.release_lease(GENERATION_LEASE, token)
        services.planner_busy = False


def generation_reservation_microusd(
    instructions: str,
    user_input: str,
    schema: Mapping[str, object],
    max_output_tokens: int,
    services: Services,
) -> int:
    """The conservative cost bound of one generation, in whole microdollars, rounded up.

    Spec 8: every input byte counts as a token, plus the schema and a fixed framing allowance,
    and the output is charged at its full token cap.
    """
    settings = services.settings
    input_bound = (
        len((instructions + user_input).encode())
        + len(json.dumps(schema).encode())
        + MESSAGE_FRAMING_TOKENS
    )
    return math.ceil(
        (
            input_bound * settings.ai_input_microusd_per_million
            + max_output_tokens * settings.ai_output_microusd_per_million
        )
        / MICROUSD_PER_MILLION
    )


def reserve_budget(services: Services, amount_microusd: int) -> None:
    """Reserve `amount_microusd` of today's AI budget before a paid call (spec 8).

    Raises `RateLimitedError` when there is no operations database or the budget cannot fund
    the amount. A reservation is never refunded, whatever the call's outcome.
    """
    if services.operations is None or not services.operations.reserve_budget(
        services.today().isoformat(), amount_microusd, services.settings.ai_daily_budget_microusd
    ):
        raise RateLimitedError(
            "The configured daily AI budget cannot fund another bounded request."
        )


def reserve_generation_budget(
    instructions: str,
    user_input: str,
    schema: Mapping[str, object],
    max_output_tokens: int,
    services: Services,
) -> None:
    """Reserve the conservative cost of one generation; see `generation_reservation_microusd`."""
    reserve_budget(
        services,
        generation_reservation_microusd(
            instructions, user_input, schema, max_output_tokens, services
        ),
    )


async def openai_json(
    instructions: str,
    user_input: str,
    schema: Mapping[str, object],
    schema_name: str,
    max_output_tokens: int,
    services: Services,
) -> str:
    """The JSON text of one OpenAI Responses generation constrained to `schema`.

    The budget is reserved first; the call uses store=false, strict json_schema output and no
    retry. Raises `httpx.HTTPError` for transport and HTTP failures, `ProviderOutputError` for
    a refusal, an incomplete output or no text, and `KeyError`/`TypeError` for a malformed
    response body. The caller validates the returned text against its own model.
    """
    reserve_generation_budget(instructions, user_input, schema, max_output_tokens, services)
    async with _client() as client:
        response = await client.post(
            OPENAI_RESPONSES_URL,
            headers=_openai_headers(services),
            json={
                "model": services.settings.ai_model,
                "store": False,
                "max_output_tokens": max_output_tokens,
                "instructions": instructions,
                "input": user_input,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
            },
        )
        response.raise_for_status()
        return _output_text(response.json())


async def openai_vector_search(
    query: str,
    vector_store_id: str,
    max_results: int,
    filters: Mapping[str, object] | None,
    services: Services,
) -> list[RetrievedPassage]:
    """At most `max_results` passages from one search of the configured vector store.

    The retrieval charge (RAG_SEARCH_MICROUSD_PER_CALL) is reserved first, separately from any
    generation. `max_results` must be 1 to `MAX_PASSAGES`. A hit without a valid `source_id`
    and `section_id` attribute or without text is dropped, since it cannot be cited; each
    passage is capped at `PASSAGE_MAX_LENGTH`. An empty list means no evidence and is not an
    error. Raises `AiUnavailableError` for an invalid store ID, bound or price, and
    `httpx.HTTPError` or `KeyError`/`TypeError` for a failed call or a malformed response body.
    """
    if not 1 <= max_results <= MAX_PASSAGES:
        raise AiUnavailableError(f"Retrieval returns 1 to {MAX_PASSAGES} passages.")
    if not VECTOR_STORE_ID_PATTERN.fullmatch(vector_store_id):
        raise AiUnavailableError("The configured vector store ID is not valid.")
    if services.settings.rag_search_microusd_per_call <= 0:
        raise AiUnavailableError("The retrieval price is not configured.")
    reserve_budget(services, services.settings.rag_search_microusd_per_call)
    body: dict[str, object] = {
        "query": query,
        "max_num_results": max_results,
        "rewrite_query": False,
    }
    if filters is not None:
        body["filters"] = dict(filters)
    async with _client() as client:
        response = await client.post(
            f"{OPENAI_VECTOR_STORES_URL}/{vector_store_id}/search",
            headers=_openai_headers(services),
            json=body,
        )
        response.raise_for_status()
        hits = response.json()["data"]
    passages = [_passage(hit) for hit in hits[:max_results]]
    return [passage for passage in passages if passage is not None]


def citation(passage: RetrievedPassage, document: DocumentSource) -> Citation:
    """The citation of a retrieved passage, filled from its manifest section (spec 5, 8).

    Every field comes from the reviewed manifest or the retrieved text, never from model text.
    Raises `ValueError` when `document` is not the manifest entry of the passage's section.
    """
    if (document.source_id, document.section_id) != (passage.source_id, passage.section_id):
        raise ValueError("The manifest section does not match the retrieved passage.")
    return Citation(
        source_id=document.source_id,
        section_id=document.section_id,
        title=document.title,
        publisher=document.publisher,
        url=document.url,
        section=document.section,
        kind=document.kind,
        passage=passage.text,
    )


def cap_passage(text: str, limit: int = PASSAGE_MAX_LENGTH) -> str:
    """`text` cut to at most `limit` characters, at a sentence end where possible.

    Spec 8: a cap should not cut a qualifier mid-sentence. The cut falls after the last
    sentence end in the second half of the allowed text, else at the last space, else at the
    limit itself.
    """
    text = text.strip()
    if len(text) <= limit:
        return text
    allowed = text[:limit]
    sentence_ends = [match.end() for match in _SENTENCE_END.finditer(text[: limit + 1])]
    usable = [end for end in sentence_ends if limit // 2 <= end <= limit]
    if usable:
        return allowed[: usable[-1]].strip()
    space = allowed.rfind(" ")
    return (allowed[:space] if space > 0 else allowed).strip()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=DEADLINE_SECONDS, follow_redirects=False, trust_env=False)


def _openai_headers(services: Services) -> dict[str, str]:
    return {"Authorization": f"Bearer {services.settings.openai_api_key}"}


def _output_text(body: Mapping[str, object]) -> str:
    """The joined output text of a Responses body; raises `ProviderOutputError` without one."""
    if body.get("status") not in (None, "completed"):
        raise ProviderOutputError("incomplete")
    output = body["output"]
    if not isinstance(output, list):
        raise TypeError("The provider output is not a list.")
    parts = [part for item in output if item.get("type") == "message" for part in item["content"]]
    if any(part.get("type") == "refusal" for part in parts):
        raise ProviderOutputError("refused")
    text = "".join(part["text"] for part in parts if part.get("type") == "output_text")
    if text == "":
        raise ProviderOutputError("empty")
    return text


def _passage(hit: Mapping[str, object]) -> RetrievedPassage | None:
    """One search hit as a passage, or None when it has no citable source, section or text."""
    attributes = hit.get("attributes")
    source_id = attributes.get("source_id") if isinstance(attributes, dict) else None
    section_id = attributes.get("section_id") if isinstance(attributes, dict) else None
    content = hit["content"]
    score = hit["score"]
    if not isinstance(content, list) or not isinstance(score, int | float):
        raise TypeError("The search hit is malformed.")
    text = cap_passage("\n".join(part["text"] for part in content if part.get("type") == "text"))
    if not isinstance(source_id, str) or not isinstance(section_id, str) or text == "":
        return None
    try:
        return RetrievedPassage(
            source_id=source_id,
            section_id=section_id,
            text=text,
            file_id=str(hit["file_id"]),
            content_sha256=hashlib.sha256(text.encode()).hexdigest(),
            score=float(score),
        )
    except ValidationError:
        return None
