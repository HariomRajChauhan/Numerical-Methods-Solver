/**
 * The ONLY place in the frontend that knows the backend URL.
 * Everything else imports these functions, which keeps a future Tauri build
 * (or a different host) a one-file change.
 */

import type {
  HealthResponse,
  MethodCatalog,
  MethodMeta,
  SolveResponse,
} from "../types/api";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const API_PREFIX = "/api";

/** Error thrown by the API client; carries the backend's friendly payload. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly hint?: string;

  constructor(message: string, options: { status?: number; code?: string; hint?: string } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status ?? 0;
    this.code = options.code ?? "error";
    this.hint = options.hint;
  }
}

interface BackendErrorBody {
  detail?: unknown;
  code?: string;
  hint?: string;
}

function messageFromBody(body: BackendErrorBody, fallback: string): string {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail) && body.detail.length > 0) {
    const first = body.detail[0] as { msg?: string };
    if (first?.msg) return first.msg;
  }
  return fallback;
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: BackendErrorBody = {};
  try {
    body = (await response.json()) as BackendErrorBody;
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(messageFromBody(body, `Request failed (${response.status}).`), {
    status: response.status,
    code: body.code ?? `http_${response.status}`,
    hint: body.hint,
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${API_PREFIX}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      "Cannot reach the solver server. Is the backend running?",
      { code: "network_error", hint: `Tried ${url}` },
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

/** Like {@link request} but for binary downloads (PDF/CSV reports). */
async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const url = `${BASE_URL}${API_PREFIX}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      "Cannot reach the solver server. Is the backend running?",
      { code: "network_error", hint: `Tried ${url}` },
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  return response.blob();
}

/** Report formats the backend can render. */
export type ExportFormat = "pdf" | "csv";

export const api = {
  /** Backend liveness probe. */
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  /** Chapter cards + every registered method (available and coming soon). */
  getCatalog(): Promise<MethodCatalog> {
    return request<MethodCatalog>("/methods");
  },

  /** Full metadata (input schema, theory, pseudocode) for one method. */
  getMethod(methodId: string): Promise<MethodMeta> {
    return request<MethodMeta>(`/methods/${encodeURIComponent(methodId)}`);
  },

  /** Run a solver. Inputs are validated by the backend schema. */
  solve(methodId: string, inputs: Record<string, unknown>): Promise<SolveResponse> {
    return request<SolveResponse>(`/solve/${encodeURIComponent(methodId)}`, {
      method: "POST",
      body: JSON.stringify(inputs),
    });
  },

  /** Download a server-rendered PDF/CSV report for a solved problem. */
  exportReport(
    methodId: string,
    inputs: Record<string, unknown>,
    format: ExportFormat = "pdf",
  ): Promise<Blob> {
    return requestBlob(`/export/${encodeURIComponent(methodId)}?format=${format}`, {
      method: "POST",
      body: JSON.stringify(inputs),
    });
  },
};
