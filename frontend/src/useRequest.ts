/**
 * A request tied to a key: when the key changes, the old request is cancelled with its
 * AbortController and a new one starts, so a stale answer never replaces a newer one.
 */

import { useEffect, useEffectEvent, useState } from "react";
import { ApiError } from "./api";

export type RequestState<T> =
  | { status: "idle" }
  /** `stale` is the last answer for an earlier key, kept on screen while the new one loads. */
  | { status: "loading"; stale: T | null }
  | { status: "done"; value: T }
  | { status: "failed"; error: ApiError };

export interface RequestOptions<T> {
  /**
   * The key the answer belongs to, when it is not the key it was asked for. The case uses it
   * after the API fills in the period, so the completed address needs no second request.
   */
  answerKey?: (value: T) => string;
  /** Called once with each answer, before the screen shows it. */
  onDone?: (value: T) => void;
}

export interface Request<T> {
  state: RequestState<T>;
  /** Asks again for the current key, for a "Try again" button. */
  retry: () => void;
}

type Answer<T> = { key: string; ok: true; value: T } | { key: string; ok: false; error: ApiError };

/**
 * Runs `load` whenever `key` changes to a key without an answer; a null key runs nothing.
 * `load` must ask for exactly what `key` names.
 */
export function useRequest<T>(
  key: string | null,
  load: (signal: AbortSignal) => Promise<T>,
  options: RequestOptions<T> = {},
): Request<T> {
  const [answer, setAnswer] = useState<Answer<T> | null>(null);
  const [attempt, setAttempt] = useState(0);

  const start = useEffectEvent((signal: AbortSignal) => load(signal));
  const isAnswered = useEffectEvent((requestKey: string) => answer?.key === requestKey);
  const finish = useEffectEvent((requestKey: string, value: T) => {
    setAnswer({ key: options.answerKey?.(value) ?? requestKey, ok: true, value });
    options.onDone?.(value);
  });

  useEffect(() => {
    if (key === null || isAnswered(key)) return;
    const controller = new AbortController();
    start(controller.signal).then(
      (value) => {
        if (!controller.signal.aborted) finish(key, value);
      },
      (error: unknown) => {
        if (!controller.signal.aborted) setAnswer({ key, ok: false, error: toApiError(error) });
      },
    );
    return () => controller.abort();
  }, [key, attempt]);

  const retry = (): void => {
    setAnswer(null);
    setAttempt((count) => count + 1);
  };
  return { state: requestState(key, answer), retry };
}

function requestState<T>(key: string | null, answer: Answer<T> | null): RequestState<T> {
  if (key === null) return { status: "idle" };
  if (answer?.key !== key) {
    return { status: "loading", stale: answer?.ok === true ? answer.value : null };
  }
  return answer.ok ? { status: "done", value: answer.value } : { status: "failed", error: answer.error };
}

/** Any failure as an ApiError, so the screen can show its message. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError("bad_response", "Something went wrong while reading the answer.");
}
