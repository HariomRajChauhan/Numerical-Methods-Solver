import { describe, expect, it } from "vitest";

import { formatCell, formatNumber, formatResultValue, tableToCsv } from "../utils/format";

describe("formatNumber", () => {
  it("trims trailing zeros", () => {
    expect(formatNumber(1.5)).toBe("1.5");
    expect(formatNumber(2.0)).toBe("2");
  });
  it("uses scientific notation for extreme magnitudes", () => {
    expect(formatNumber(1.23e-7)).toContain("e");
    expect(formatNumber(4.5e8)).toContain("e");
  });
  it("handles zero and precision", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(1 / 3, 3)).toBe("0.333");
  });
});

describe("formatCell", () => {
  it("renders null as a dash and booleans as words", () => {
    expect(formatCell(null)).toBe("—");
    expect(formatCell(true)).toBe("true");
  });
});

describe("formatResultValue", () => {
  it("renders arrays inline", () => {
    expect(formatResultValue([1, 2.5])).toBe("[1, 2.5]");
  });
  it("renders strings and numbers", () => {
    expect(formatResultValue("hello")).toBe("hello");
    expect(formatResultValue(1.25)).toBe("1.25");
  });
});

describe("tableToCsv", () => {
  it("writes a header row and data rows", () => {
    const csv = tableToCsv({
      title: "Iterations",
      columns: ["n", "x"],
      rows: [
        [0, 1],
        [1, 2],
      ],
    });
    expect(csv).toBe("n,x\n0,1\n1,2");
  });

  it("quotes fields containing commas", () => {
    const csv = tableToCsv({ title: "t", columns: ["a"], rows: [["x,y"]] });
    expect(csv).toBe('a\n"x,y"');
  });
});
