import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";
import { useBackendConnectionStore } from "../store/connection";
import { defaultInputs, useSolverStore } from "../store/solver";
import type { MethodMeta, SolveResponse } from "../types/api";

const META: MethodMeta = {
  id: "bisection",
  chapter: "ch1_nonlinear",
  variables: ["x"],
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

afterEach(() => {
  vi.restoreAllMocks();
  useBackendConnectionStore.setState({
    status: "checking",
    error: undefined,
    lastReadyAt: undefined,
  });
});

describe("solver readiness", () => {
  it("does not POST a solve while the backend is unavailable and keeps inputs", async () => {
    const solve = vi.spyOn(api, "solve");
    useBackendConnectionStore.setState({
      status: "error",
      error: new ApiError("offline", { code: "backend_unavailable" }),
      lastReadyAt: undefined,
    });
    useSolverStore.getState().initialize(META);
    useSolverStore.getState().setInput("function", "x^2 - 2");
    const before = useSolverStore.getState().inputs;

    await useSolverStore.getState().run(META);

    expect(solve).not.toHaveBeenCalled();
    expect(useSolverStore.getState().inputs).toEqual(before);
    expect(useSolverStore.getState().status).toBe("error");
  });

  it("sends the solve request once the backend is ready", async () => {
    const response = {
      method: "bisection",
      status: "converged",
      result: { root: 1 },
      steps: [],
      tables: [],
      plot: null,
      error: null,
      warnings: [],
      pseudocode: "",
      python_source: "",
    } as unknown as SolveResponse;
    const solve = vi.spyOn(api, "solve").mockResolvedValue(response);
    useBackendConnectionStore.setState({ status: "ready", error: undefined });
    useSolverStore.getState().initialize(META);

    await useSolverStore.getState().run(META);

    expect(solve).toHaveBeenCalledWith("bisection", useSolverStore.getState().inputs);
    expect(useSolverStore.getState().status).toBe("done");
  });
});
