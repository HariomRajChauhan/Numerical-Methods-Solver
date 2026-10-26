/**
 * Shareable solver state.
 *
 * The URL stays on the canonical /methods/<id> route; the encoded payload only
 * carries input values and the active result view. Results themselves are never
 * encoded, so a shared link always re-solves on the recipient's machine.
 */

export const SHARE_STATE_PARAM = "s";
const VERSION = 1;

export interface ShareState {
  method: string;
  inputs: Record<string, unknown>;
  tab?: string;
}

interface SharePayload {
  v: number;
  m: string;
  i: Record<string, unknown>;
  t?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function encodeBase64Url(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export function encodeShareState(state: ShareState): string {
  const payload: SharePayload = {
    v: VERSION,
    m: state.method,
    i: state.inputs,
    ...(state.tab ? { t: state.tab } : {}),
  };
  return encodeBase64Url(JSON.stringify(payload));
}

export function decodeShareState(value: string | null | undefined): ShareState | null {
  if (!value) return null;
  try {
    const parsed: unknown = JSON.parse(decodeBase64Url(value));
    if (!isRecord(parsed)) return null;
    if (parsed.v !== VERSION || typeof parsed.m !== "string" || !isRecord(parsed.i)) return null;
    return {
      method: parsed.m,
      inputs: parsed.i,
      ...(typeof parsed.t === "string" ? { tab: parsed.t } : {}),
    };
  } catch {
    return null;
  }
}

/** Build the canonical share URL for the current method, inputs and tab. */
export function buildShareUrl(
  method: string,
  inputs: Record<string, unknown>,
  tab: string | undefined,
  base: string = window.location.href,
): string {
  const url = new URL(`/methods/${encodeURIComponent(method)}`, base);
  url.searchParams.set(SHARE_STATE_PARAM, encodeShareState({ method, inputs, tab }));
  return url.toString();
}

/** Read and decode the shared state from a location search string. */
export function readShareState(search: string = window.location.search): ShareState | null {
  return decodeShareState(new URLSearchParams(search).get(SHARE_STATE_PARAM));
}
