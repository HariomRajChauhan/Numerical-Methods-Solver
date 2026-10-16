import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MethodForm } from "../components/MethodForm";
import type { MethodMeta } from "../types/api";

/** A bisection-shaped schema — copied from GET /api/methods/bisection. */
const BISECTION: MethodMeta = {
  id: "bisection",
  chapter: "ch1_nonlinear",
  name: "Bisection Method",
  status: "available",
  summary: "",
  theory: "",
  pseudocode: "",
  formulas: [],
  chapter_title: "Non-linear Equations",
  chapter_number: 1,
  input_schema: [
    {
      key: "function",
      label: "Function f(x)",
      type: "function",
      required: true,
      default: null,
      help: "",
      placeholder: "x^3 - x - 1",
      min: null,
      max: null,
      variable: "x",
      rows: null,
      cols: null,
      options: [],
    },
    {
      key: "a",
      label: "Lower bound a",
      type: "number",
      required: true,
      default: 1,
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
      key: "b",
      label: "Upper bound b",
      type: "number",
      required: true,
      default: 2,
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
      key: "tolerance",
      label: "Tolerance (stopping error)",
      type: "tolerance",
      required: true,
      default: 1e-6,
      help: "",
      placeholder: "",
      min: 1e-15,
      max: 1,
      variable: null,
      rows: null,
      cols: null,
      options: [],
    },
    {
      key: "max_iterations",
      label: "Maximum iterations",
      type: "max_iterations",
      required: true,
      default: 50,
      help: "",
      placeholder: "",
      min: 1,
      max: 10000,
      variable: null,
      rows: null,
      cols: null,
      options: [],
    },
  ],
  examples: [
    {
      name: "Cubic: x³ - x - 1 on [1, 2]",
      description: "",
      inputs: { function: "x^3 - x - 1", a: 1, b: 2, tolerance: 1e-6, max_iterations: 50 },
    },
  ],
};

function renderForm(overrides: Partial<Parameters<typeof MethodForm>[0]> = {}) {
  const props = {
    meta: BISECTION,
    inputs: { function: "", a: 1, b: 2, tolerance: 1e-6, max_iterations: 50 },
    status: "idle" as const,
    onChange: vi.fn(),
    onSubmit: vi.fn(),
    onClear: vi.fn(),
    onLoadExample: vi.fn(),
    ...overrides,
  };
  render(<MethodForm {...props} />);
  return props;
}

describe("MethodForm (schema-driven)", () => {
  it("renders one labelled control per schema field, with no method-specific code", () => {
    renderForm();
    expect(screen.getByLabelText(/Function f\(x\)/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Lower bound a/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Upper bound b/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tolerance/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Maximum iterations/)).toBeInTheDocument();
  });

  it("pre-fills scalar defaults from the schema", () => {
    renderForm();
    expect(screen.getByLabelText(/Lower bound a/)).toHaveValue(1);
    expect(screen.getByLabelText(/Upper bound b/)).toHaveValue(2);
  });

  it("lists examples from the metadata", () => {
    renderForm();
    expect(screen.getByRole("option", { name: /Cubic: x³ - x - 1/ })).toBeInTheDocument();
  });

  it("reports edits with the field key", () => {
    const props = renderForm();
    fireEvent.change(screen.getByLabelText(/Function f\(x\)/), {
      target: { value: "x^2 - 2" },
    });
    expect(props.onChange).toHaveBeenCalledWith("function", "x^2 - 2");
  });

  it("submits the form", () => {
    const props = renderForm();
    const form = screen.getByRole("button", { name: "Solve" }).closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);
    expect(props.onSubmit).toHaveBeenCalledTimes(1);
  });
});
