import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import { backendUnavailableError, waitForBackendReady } from "../store/connection";
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
  const [attempt, setAttempt] = useState<{ methodId?: string; count: number }>({ count: 0 });
  const key = methodId ? `${methodId}:${attempt.count}` : "";
  const reload = () =>
    setAttempt((value) => ({ methodId, count: value.count + 1 }));

  useEffect(() => {
    if (!methodId) return;
    const requestKey = `${methodId}:${attempt.count}`;
    const restartOnError = attempt.methodId === methodId && attempt.count > 0;
    let cancelled = false;

    async function loadMeta(): Promise<void> {
      const ready = await waitForBackendReady(restartOnError);
      if (cancelled) return;
      if (!ready) {
        setResolved({ key: requestKey, error: backendUnavailableError() });
        return;
      }
      try {
        const meta = await api.getMethod(methodId as string);
        if (!cancelled) setResolved({ key: requestKey, meta });
      } catch (error) {
        if (cancelled) return;
        setResolved({
          key: requestKey,
          error: error instanceof ApiError ? error : new ApiError("Failed to load the method."),
        });
      }
    }

    void loadMeta();
    return () => {
      cancelled = true;
    };
  }, [methodId, attempt.count, attempt.methodId]);

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
