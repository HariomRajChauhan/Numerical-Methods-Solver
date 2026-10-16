import { describe, expect, it } from "vitest";

import { defaultInputs } from "../store/solver";
import type { MethodMeta } from "../types/api";

const META: MethodMeta = {
  id: "bisection",
  chapter: "ch1_nonlinear",
  name: "Bisection",
  status: "available",
  summary: "",
  theory: "",
  pseudocode: "",
  formulas: [],
  chapter_title: "Non-linear Equations",
  chapter_number: 1,
  examples: [],
  input_schema: [
    {
      key: "function",
      label: "f(x)",
      type: "function",
      required: true,
      default: null,
      help: "",
      placeholder: "",
      min: null,
      max: null,
      variable: "x",
      rows: null,
      cols: null,
      options: [],
    },
    {
      key: "tolerance",
      label: "Tolerance",
      type: "tolerance",
      required: false,
      default: 1e-6,
      help: "",
      placeholder: "",
      min: null,
      max: null,
      variable: null,
      rows: null,
      cols: null,
      options: [],
    },
    {
      key: "matrix",
      label: "Augmented matrix",
      type: "matrix",
      required: true,
      default: null,
      help: "",
      placeholder: "",
      min: null,
      max: null,
      variable: null,
      rows: 2,
      cols: 3,
      options: [],
    },
  ],
};

describe("defaultInputs", () => {
  it("uses schema defaults when present", () => {
    const inputs = defaultInputs(META);
    expect(inputs.tolerance).toBe(1e-6);
  });

  it("builds an empty matrix of the declared size", () => {
    const inputs = defaultInputs(META);
    expect(inputs.matrix).toEqual([
      [0, 0, 0],
      [0, 0, 0],
    ]);
  });

  it("starts text/function fields as empty strings", () => {
    const inputs = defaultInputs(META);
    expect(inputs.function).toBe("");
  });
});
