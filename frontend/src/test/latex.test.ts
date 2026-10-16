import { describe, expect, it } from "vitest";

import { renderLatex } from "../utils/latex";

describe("renderLatex", () => {
  it("renders a simple expression to KaTeX HTML", () => {
    const html = renderLatex("x^2 + 1");
    expect(html).toContain("katex");
    expect(html).toContain("x");
  });

  it("renders display mode with the katex-display class", () => {
    expect(renderLatex("\\frac{1}{2}", true)).toContain("katex-display");
  });

  it("does not throw on malformed latex", () => {
    expect(() => renderLatex("\\frac{1}{")).not.toThrow();
  });

  it("returns an empty string for empty input", () => {
    expect(renderLatex("")).toBe("");
  });
});
