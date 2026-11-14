/**
 * One conversation with the built-in AI (spec 8): sends each question with the earlier turns as
 * plain text, follows the stream, and hands each case or map the AI ran to the screen.
 */

import { useEffect, useReducer, useRef } from "react";
import { streamChat } from "./api";
import type { ChatEvent, ChatRequest } from "./api";
import { chatReducer, chatResult, conversationMessages, EMPTY_CHAT, isRunning } from "./chat";
import type { ChatResult, ChatState } from "./chat";
import { toApiError } from "./useRequest";

export type AskOutcome =
  | { kind: "answered" }
  | { kind: "stopped" }
  /** `showedResult` is true when the turn put a case or a map on screen before it failed. */
  | { kind: "failed"; message: string; showedResult: boolean };

export interface Chat {
  state: ChatState;
  running: boolean;
  /**
   * Asks `question` about the case whose parameter string is `caseQuery`, if one is on screen.
   * `onResult` gets each case or map as it arrives. Resolves when the turn ends; never rejects.
   */
  ask: (
    question: string,
    caseQuery: string | undefined,
    onResult: (result: ChatResult) => void,
  ) => Promise<AskOutcome>;
  stop: () => void;
  /** Forgets the conversation, stopping a turn that is still running. */
  reset: () => void;
}

export function useChat(): Chat {
  const [state, dispatch] = useReducer(chatReducer, EMPTY_CHAT);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const stop = (): void => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    dispatch({ type: "stopped" });
  };

  const ask = async (
    question: string,
    caseQuery: string | undefined,
    onResult: (result: ChatResult) => void,
  ): Promise<AskOutcome> => {
    if (controllerRef.current !== null) stop();
    const controller = new AbortController();
    controllerRef.current = controller;
    const request: ChatRequest = { messages: conversationMessages(state, question) };
    if (caseQuery !== undefined) request.case = caseQuery;
    dispatch({ type: "asked", question });

    const turn = { failure: null as string | null, showedResult: false };
    const handle = (event: ChatEvent): void => {
      if (controller.signal.aborted) return;
      dispatch({ type: "event", event });
      if (event.event === "error") turn.failure = event.data.message;
      if (event.event !== "case") return;
      const result = chatResult(event.data);
      if (result === null) return;
      turn.showedResult = true;
      onResult(result);
    };

    try {
      await streamChat(request, handle, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) return { kind: "stopped" };
      turn.failure = toApiError(error).message;
      dispatch({ type: "failed", message: turn.failure });
    } finally {
      if (controllerRef.current === controller) controllerRef.current = null;
    }
    if (turn.failure !== null)
      return { kind: "failed", message: turn.failure, showedResult: turn.showedResult };
    return { kind: "answered" };
  };

  const reset = (): void => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    dispatch({ type: "reset" });
  };

  return { state, running: isRunning(state), ask, stop, reset };
}
