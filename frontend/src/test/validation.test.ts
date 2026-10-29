import { describe, expect, it } from "vitest";

import type { InputField, MethodMeta } from "../types/api";
import { validateInputs } from "../utils/validation";

const BASE_FIELD: InputField = {
  key: "value",
  label: "Value",
  type: "text",
  required: true,
  default: null,
  help: "",
  placeholder: "",
  min: null,
  max: null,
  variable: null,
  rows: null,
  cols: null,
  options: [],
};

function field(overrides: Partial<InputField>): InputField {
  return { ...BASE_FIELD, ...overrides };
}

function meta(inputSchema: InputField[]): MethodMeta {
  return {
    id: "test_method",
    chapter: "ch1_nonlinear",
    variables: ["x"],
    name: "Test Method",
    status: "available",
    summary: "",
    theory: "",
    pseudocode: "",
    formulas: [],
    chapter_title: "Non-linear Equations",
    chapter_number: 1,
    input_schema: inputSchema,
    examples: [],
  };
}

describe("validateInputs", () => {
  it("requires empty required fields", () => {
    const errors = validateInputs(meta([field({ key: "function", label: "Function f(x)" })]), {
      function: "   ",
    });
    expect(errors.function).toBe("Function f(x) is required.");
  });

  it("allows empty optional fields", () => {
    const errors = validateInputs(
      meta([field({ key: "note", label: "Note", type: "text", required: false })]),
      { note: "" },
    );
    expect(errors).toEqual({});
  });

  it("checks numeric ranges and tolerance", () => {
    const errors = validateInputs(
      meta([
        field({ key: "a", label: "Lower bound", type: "number", min: 0, max: 10 }),
        field({ key: "tolerance", label: "Tolerance", type: "tolerance", min: 1e-15, max: 1 }),
      ]),
      { a: 12, tolerance: 0 },
    );
    expect(errors.a).toBe("Lower bound must be at most 10.");
    expect(errors.tolerance).toBe("Tolerance must be greater than zero.");
  });

  it("requires whole-number iteration counts", () => {
    const errors = validateInputs(
      meta([field({ key: "max_iterations", label: "Maximum iterations", type: "max_iterations" })]),
      { max_iterations: 2.5 },
    );
    expect(errors.max_iterations).toBe("Maximum iterations must be a whole number of at least 1.");
  });

  it("rejects malformed matrices", () => {
    const errors = validateInputs(
      meta([field({ key: "matrix", label: "Matrix A", type: "matrix" })]),
      { matrix: [["1", "2"], ["", "4"]] },
    );
    expect(errors.matrix).toBe("Every matrix cell must contain a number.");
  });

  it("rejects malformed data-point pairs", () => {
    const errors = validateInputs(
      meta([field({ key: "points", label: "Data points", type: "data_points" })]),
      { points: "0,1; 1" },
    );
    expect(errors.points).toContain("one x,y pair per line");
  });

  it("accepts a complete valid input set", () => {
    const errors = validateInputs(
      meta([
        field({ key: "function", label: "Function f(x)", type: "function", variable: "x" }),
        field({ key: "a", label: "Lower bound", type: "number" }),
        field({ key: "vector", label: "Initial vector", type: "vector" }),
        field({ key: "points", label: "Data points", type: "data_points" }),
      ]),
      { function: "x^3 - x - 1", a: "1", vector: "1, 2, 3", points: "0,1; 1,0.5" },
    );
    expect(errors).toEqual({});
  });
});
