import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import type { MethodMeta } from "../types/api";

interface MethodState {
  meta?: MethodMeta;
  loading: boolean;
  error?: ApiError;
}

interface Resolved {
  id: string;
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

  useEffect(() => {
    if (!methodId) return;
    let cancelled = false;
    api
      .getMethod(methodId)
      .then((meta) => {
        if (!cancelled) setResolved({ id: methodId, meta });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setResolved({
          id: methodId,
          error: error instanceof ApiError ? error : new ApiError("Failed to load the method."),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [methodId]);

  if (!methodId) {
    return { loading: false, error: new ApiError("No method was selected.") };
  }
  const current = resolved?.id === methodId ? resolved : undefined;
  return {
    loading: current === undefined,
    meta: current?.meta,
    error: current?.error,
  };
}
