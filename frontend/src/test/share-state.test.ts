import { describe, expect, it } from "vitest";

import {
  SHARE_STATE_PARAM,
  buildShareUrl,
  decodeShareState,
  encodeShareState,
  readShareState,
} from "../utils/shareState";

describe("share state", () => {
  it("round-trips inputs and the active tab through a URL-safe payload", () => {
    const encoded = encodeShareState({
      method: "bisection",
      inputs: {
        function: "x^2 - \u221a2",
        a: 1,
        b: 2,
        matrix: [
          ["1", "2"],
          ["3", "4"],
        ],
      },
      tab: "graph",
    });

    expect(encoded).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(decodeShareState(encoded)).toEqual({
      method: "bisection",
      inputs: {
        function: "x^2 - \u221a2",
        a: 1,
        b: 2,
        matrix: [
          ["1", "2"],
          ["3", "4"],
        ],
      },
      tab: "graph",
    });
  });

  it("builds a canonical method URL with the encoded state", () => {
    const url = buildShareUrl(
      "bisection",
      { function: "x^3 - x - 1", a: 1, b: 2 },
      "steps",
      "https://solver.example/old/path?keep=no",
    );
    const parsed = new URL(url);

    expect(parsed.origin).toBe("https://solver.example");
    expect(parsed.pathname).toBe("/methods/bisection");
    expect(parsed.searchParams.get("keep")).toBeNull();
    expect(parsed.searchParams.get(SHARE_STATE_PARAM)).toBeTruthy();
    expect(readShareState(parsed.search)).toEqual({
      method: "bisection",
      inputs: { function: "x^3 - x - 1", a: 1, b: 2 },
      tab: "steps",
    });
  });

  it("rejects malformed or unsupported payloads", () => {
    expect(decodeShareState(null)).toBeNull();
    expect(decodeShareState("not-base64")).toBeNull();
    expect(decodeShareState(btoa(JSON.stringify({ v: 99, m: "bisection", i: {} })))).toBeNull();
    expect(readShareState("?s=")).toBeNull();
  });
});
