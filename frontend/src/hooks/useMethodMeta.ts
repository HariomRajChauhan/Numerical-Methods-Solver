import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import type { MethodMeta } from "../types/api";

interface MethodState {
  meta?: MethodMeta;
  loading: boolean;
  error?: ApiError;
  reload: () => void;
}

interface Resolved {
  key: string;
  meta?: MethodMeta;
  error?: ApiError;
}

/**
 * Fetch a single method's metadata by id.
 * Loading is derived from the resolved cache, so switching methods shows the
 * skeleton immediately without a synchronous state update in the effect.
 */
export function useMethodMeta(methodId: string | undefined): MethodState {
  const [resolved, setResolved] = useState<Resolved>();
  const [attempt, setAttempt] = useState(0);
  const key = methodId ? `${methodId}:${attempt}` : "";
  const reload = () => setAttempt((value) => value + 1);

  useEffect(() => {
    if (!methodId) return;
    const requestKey = `${methodId}:${attempt}`;
    let cancelled = false;
    api
      .getMethod(methodId)
      .then((meta) => {
        if (!cancelled) setResolved({ key: requestKey, meta });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setResolved({
          key: requestKey,
          error: error instanceof ApiError ? error : new ApiError("Failed to load the method."),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [methodId, attempt]);

  if (!methodId) {
    return {
      loading: false,
      error: new ApiError("No method was selected."),
      reload,
    };
  }
  const current = resolved?.key === key ? resolved : undefined;
  return {
    loading: current === undefined,
    meta: current?.meta,
    error: current?.error,
    reload,
  };
}
