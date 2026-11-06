import { create } from "zustand";

import { api, ApiError } from "../api/client";

/**
 * Shared backend readiness state.
 *
 * Render's free tier spins the API down after a period of inactivity. The first
 * request to a sleeping service can take 30–60 seconds (and may fail with a
 * 502/503/504 while it boots), so readiness is tracked centrally and every
 * backend consumer waits on the same single-flight wake-up cycle.
 */
export type BackendConnectionStatus = "checking" | "waking" | "ready" | "error";

export interface BackendConnectionState {
  status: BackendConnectionStatus;
  /** Set when the retry window expires or a permanent configuration error occurs. */
  error?: ApiError;
  /** Timestamp of the last successful health response. */
  lastReadyAt?: number;
}

/** How long a request may take before we abort it and try again. */
const HEALTH_TIMEOUT_MS = 75_000;
/** Total time the automatic wake-up cycle may spend trying. */
const MAX_WAKE_DURATION_MS = 150_000;
/** Delay after the first failed attempt, then after each subsequent failure. */
const RETRY_DELAYS_MS = [2_000, 5_000, 10_000, 20_000, 30_000];
/** Keep "checking" quiet briefly; switch to "waking" if the server is slow. */
const CHECKING_GRACE_MS = 2_500;

export const useBackendConnectionStore = create<BackendConnectionState>()(() => ({
  status: "checking",
  error: undefined,
  lastReadyAt: undefined,
}));

let wakePromise: Promise<boolean> | null = null;
let deadline = 0;
let attempt = 0;
let abortController: AbortController | null = null;
let graceTimer: ReturnType<typeof setTimeout> | undefined;
let retryTimer: ReturnType<typeof setTimeout> | undefined;

function setState(partial: Partial<BackendConnectionState>): void {
  useBackendConnectionStore.setState(partial);
}

function clearTimers(): void {
  if (graceTimer !== undefined) {
    clearTimeout(graceTimer);
    graceTimer = undefined;
  }
  if (retryTimer !== undefined) {
    clearTimeout(retryTimer);
    retryTimer = undefined;
  }
}

function scheduleGraceTimer(): void {
  if (graceTimer !== undefined) clearTimeout(graceTimer);
  graceTimer = setTimeout(() => {
    graceTimer = undefined;
    if (useBackendConnectionStore.getState().status === "checking") {
      setState({ status: "waking" });
    }
  }, CHECKING_GRACE_MS);
}

function markReady(): void {
  clearTimers();
  setState({ status: "ready", error: undefined, lastReadyAt: Date.now() });
}

function failureFor(lastError?: ApiError): ApiError {
  if (lastError?.status === 404) {
    return new ApiError("The solver health endpoint could not be found.", {
      status: lastError.status,
      code: "backend_unavailable",
      hint: "The backend health path may be misconfigured (expected /api/health).",
    });
  }
  return new ApiError("Unable to connect to the solver.", {
    status: lastError?.status,
    code: "backend_unavailable",
    hint: "The free solver server may still be starting. Check your connection and try again.",
  });
}

function markFailed(lastError?: ApiError): false {
  clearTimers();
  abortController = null;
  setState({ status: "error", error: failureFor(lastError) });
  return false;
}

/** Network failures, timeouts and platform startup responses are retryable. */
function isTransient(error: ApiError): boolean {
  if (error.code === "timeout" || error.status === 0) return true;
  if (error.status >= 500) return true;
  return error.status === 408 || error.status === 425 || error.status === 429;
}

function nextRetryDelay(): number {
  return RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)];
}

/** Pause retries while the tab is hidden; don't burn the retry window while nobody is looking. */
async function pauseWhileHidden(): Promise<void> {
  if (typeof document === "undefined" || !document.hidden) return;
  const hiddenAt = Date.now();
  await new Promise<void>((resolve) => {
    function handleVisibilityChange(): void {
      if (!document.hidden) {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
        resolve();
      }
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });
  deadline += Date.now() - hiddenAt;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    retryTimer = setTimeout(resolve, ms);
  });
}

async function checkHealthOnce(): Promise<void> {
  const controller = new AbortController();
  abortController = controller;
  let timedOut = false;
  const timeout = Math.max(
    1,
    Math.min(HEALTH_TIMEOUT_MS, deadline - Date.now()),
  );
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeout);

  try {
    const response = await api.health(controller.signal);
    if (response.status !== "ok") {
      throw new ApiError("The solver reported that it is not ready yet.", {
        code: "backend_not_ready",
      });
    }
  } catch (error) {
    if (timedOut || controller.signal.aborted) {
      throw new ApiError("The solver health check timed out.", { code: "timeout" });
    }
    throw error instanceof ApiError
      ? error
      : new ApiError("Cannot reach the solver server.", { code: "network_error" });
  } finally {
    clearTimeout(timeoutId);
    if (abortController === controller) abortController = null;
  }
}

async function runWakeCycle(): Promise<boolean> {
  let lastError: ApiError | undefined;

  while (true) {
    await pauseWhileHidden();
    if (Date.now() >= deadline) return markFailed(lastError);

    try {
      await checkHealthOnce();
      markReady();
      return true;
    } catch (error) {
      lastError =
        error instanceof ApiError
          ? error
          : new ApiError("Cannot reach the solver server.", { code: "network_error" });
      if (!isTransient(lastError)) return markFailed(lastError);
    }

    clearTimers();
    setState({ status: "waking" });

    const delay = nextRetryDelay();
    attempt += 1;
    if (Date.now() + delay >= deadline) return markFailed(lastError);

    await sleep(delay);
  }
}

function beginWakeCycle(): Promise<boolean> {
  if (wakePromise) return wakePromise;

  deadline = Date.now() + MAX_WAKE_DURATION_MS;
  attempt = 0;
  setState({ status: "checking", error: undefined });
  scheduleGraceTimer();

  const cycle = runWakeCycle().finally(() => {
    clearTimers();
    abortController = null;
    wakePromise = null;
  });
  wakePromise = cycle;
  return cycle;
}

/**
 * Start the automatic wake-up on a fresh visit.
 *
 * Safe to call from every mount (including React Strict Mode): once a cycle is
 * running, or once the connection is ready/failed, additional calls are no-ops.
 */
export function startBackendWake(): void {
  const { status } = useBackendConnectionStore.getState();
  if (status === "ready" || status === "error") return;
  if (!wakePromise) void beginWakeCycle();
}

/**
 * Wait for the shared backend wake-up.
 *
 * Pass `restartOnError` from explicit user actions (retry, solve, export) so a
 * failed cycle can be started again without waiting for a page reload.
 */
export function waitForBackendReady(restartOnError = false): Promise<boolean> {
  const { status } = useBackendConnectionStore.getState();
  if (status === "ready") return Promise.resolve(true);
  if (status === "error") {
    return restartOnError ? beginWakeCycle() : Promise.resolve(false);
  }
  return wakePromise ?? beginWakeCycle();
}

/** Manual retry after the automatic retry window has expired. */
export function retryBackendConnection(): Promise<boolean> {
  if (wakePromise) return wakePromise;
  if (useBackendConnectionStore.getState().status === "ready") return Promise.resolve(true);
  return beginWakeCycle();
}

/** Reusable friendly error for features that depend on the backend. */
export function backendUnavailableError(): ApiError {
  return useBackendConnectionStore.getState().error ?? failureFor();
}
