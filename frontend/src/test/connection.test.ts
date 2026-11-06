import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const HEALTHY = { status: "ok", service: "Numerical Methods Solver", version: "0.1.0" };

async function loadConnection() {
  vi.resetModules();
  const { api, ApiError } = await import("../api/client");
  const health = vi.spyOn(api, "health");
  const connection = await import("../store/connection");
  return { health, connection, ApiError };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("backend connection manager", () => {
  it("shares one in-flight health request between consumers", async () => {
    const { health, connection } = await loadConnection();
    health.mockResolvedValue(HEALTHY);

    const [first, second] = await Promise.all([
      connection.waitForBackendReady(),
      connection.waitForBackendReady(),
    ]);

    expect(first).toBe(true);
    expect(second).toBe(true);
    expect(health).toHaveBeenCalledTimes(1);
    expect(connection.useBackendConnectionStore.getState().status).toBe("ready");
  });

  it("is idempotent when started more than once (Strict Mode mounts)", async () => {
    const { health, connection } = await loadConnection();
    health.mockResolvedValue(HEALTHY);

    connection.startBackendWake();
    connection.startBackendWake();
    expect(await connection.waitForBackendReady()).toBe(true);

    expect(health).toHaveBeenCalledTimes(1);
  });

  it("does not report ready before the health endpoint responds", async () => {
    const { health, connection } = await loadConnection();
    let resolveHealth!: (value: typeof HEALTHY) => void;
    health.mockReturnValue(
      new Promise<typeof HEALTHY>((resolve) => {
        resolveHealth = resolve;
      }),
    );

    const ready = connection.waitForBackendReady();
    await Promise.resolve();
    expect(connection.useBackendConnectionStore.getState().status).toBe("checking");

    await vi.advanceTimersByTimeAsync(2_500);
    expect(connection.useBackendConnectionStore.getState().status).toBe("waking");

    resolveHealth(HEALTHY);
    expect(await ready).toBe(true);
    expect(connection.useBackendConnectionStore.getState().status).toBe("ready");
  });

  it("retries transient failures with backoff and then becomes ready", async () => {
    const { health, connection, ApiError } = await loadConnection();
    health
      .mockRejectedValueOnce(new ApiError("offline", { code: "network_error" }))
      .mockResolvedValueOnce(HEALTHY);

    const ready = connection.waitForBackendReady();
    await vi.advanceTimersByTimeAsync(0);
    expect(connection.useBackendConnectionStore.getState().status).toBe("waking");

    await vi.advanceTimersByTimeAsync(2_000);
    expect(await ready).toBe(true);
    expect(health).toHaveBeenCalledTimes(2);
    expect(connection.useBackendConnectionStore.getState().status).toBe("ready");
  });

  it("pauses retries while the tab is hidden", async () => {
    const { health, connection, ApiError } = await loadConnection();
    health
      .mockRejectedValueOnce(new ApiError("offline", { code: "network_error" }))
      .mockResolvedValueOnce(HEALTHY);

    const ready = connection.waitForBackendReady();
    await vi.advanceTimersByTimeAsync(0);
    expect(health).toHaveBeenCalledTimes(1);

    const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    await vi.advanceTimersByTimeAsync(5_000);
    expect(health).toHaveBeenCalledTimes(1);

    hidden.mockReturnValue(false);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(await ready).toBe(true);
    expect(health).toHaveBeenCalledTimes(2);
  });

  it("stops after the bounded retry window and exposes a retryable error", async () => {
    const { health, connection, ApiError } = await loadConnection();
    health.mockRejectedValue(new ApiError("offline", { code: "network_error" }));

    const ready = connection.waitForBackendReady();
    await vi.advanceTimersByTimeAsync(200_000);

    expect(await ready).toBe(false);
    const state = connection.useBackendConnectionStore.getState();
    expect(state.status).toBe("error");
    expect(state.error?.code).toBe("backend_unavailable");
    expect(health.mock.calls.length).toBeLessThan(10);
  });

  it("fails fast for a non-transient configuration error", async () => {
    const { health, connection, ApiError } = await loadConnection();
    health.mockRejectedValue(
      new ApiError("not found", { status: 404, code: "http_404" }),
    );

    expect(await connection.waitForBackendReady()).toBe(false);
    expect(health).toHaveBeenCalledTimes(1);
    expect(connection.useBackendConnectionStore.getState().error?.message).toContain(
      "health endpoint",
    );
  });

  it("does not repeat the health request once ready", async () => {
    const { health, connection } = await loadConnection();
    health.mockResolvedValue(HEALTHY);

    expect(await connection.waitForBackendReady()).toBe(true);
    expect(await connection.waitForBackendReady()).toBe(true);

    expect(health).toHaveBeenCalledTimes(1);
  });
});
