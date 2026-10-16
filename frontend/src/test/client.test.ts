import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("returns parsed JSON on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ status: "ok", service: "nms", version: "0.1.0" }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const health = await api.health();
    expect(health.status).toBe("ok");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
  });

  it("maps a friendly backend error body onto ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "f(x) is not valid.", code: "bad_function", hint: "Check syntax" }, 422),
      ),
    );

    await expect(api.solve("bisection", {})).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      code: "bad_function",
      hint: "Check syntax",
      message: "f(x) is not valid.",
    });
  });

  it("extracts the first validation message from a detail array", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: [{ msg: "field required" }] }, 422)),
    );

    await expect(api.solve("bisection", {})).rejects.toThrow("field required");
  });

  it("falls back to a status message when the body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));

    const error = (await api.getCatalog().catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(500);
    expect(error.code).toBe("http_500");
  });

  it("reports a network error when fetch rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed to fetch")));

    await expect(api.getMethod("bisection")).rejects.toMatchObject({ code: "network_error" });
  });

  it("downloads a report as a Blob", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(new Blob(["%PDF-1.4"], { type: "application/pdf" }), {
        status: 200,
        headers: { "Content-Type": "application/pdf" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const blob = await api.exportReport("bisection", { a: 1, b: 2 }, "pdf");
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe("application/pdf");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/export/bisection?format=pdf",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("maps a failed export onto ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "not implemented yet", code: "method_unavailable" }, 409),
      ),
    );

    await expect(api.exportReport("newton_raphson", {}, "csv")).rejects.toMatchObject({
      status: 409,
      code: "method_unavailable",
      message: "not implemented yet",
    });
  });
});
