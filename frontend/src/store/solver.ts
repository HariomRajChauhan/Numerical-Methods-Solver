import { create } from "zustand";

import { api, ApiError } from "../api/client";
import type { InputField, MethodMeta, SolveResponse } from "../types/api";

/** Build the initial input state for a method from its schema defaults. */
export function defaultInputs(meta: MethodMeta): Record<string, unknown> {
  const inputs: Record<string, unknown> = {};
  for (const field of meta.input_schema) {
    inputs[field.key] = defaultForField(field);
  }
  return inputs;
}

function defaultForField(field: InputField): unknown {
  if (field.default !== null && field.default !== undefined) return field.default;
  switch (field.type) {
    case "matrix":
      return emptyMatrix(field.rows ?? 3, field.cols ?? (field.rows ?? 3) + 1);
    case "vector":
    case "data_points":
      return "";
    case "boolean":
      return false;
    case "function":
    case "text":
    case "select":
    case "number":
    case "integer":
    case "tolerance":
    case "max_iterations":
    case "precision":
    default:
      return "";
  }
}

function emptyMatrix(rows: number, cols: number): number[][] {
  return Array.from({ length: Math.max(1, rows) }, () => Array.from({ length: Math.max(1, cols) }, () => 0));
}

interface SolverState {
  methodId: string;
  inputs: Record<string, unknown>;
  status: "idle" | "loading" | "error" | "done";
  response?: SolveResponse;
  error?: ApiError;
  /** Prepare the form for a method (defaults + example loading). */
  initialize: (meta: MethodMeta) => void;
  setInput: (key: string, value: unknown) => void;
  loadExample: (inputs: Record<string, unknown>, meta: MethodMeta) => void;
  run: (meta: MethodMeta) => Promise<void>;
  clearResult: () => void;
}

export const useSolverStore = create<SolverState>()((set, get) => ({
  methodId: "",
  inputs: {},
  status: "idle",
  response: undefined,
  error: undefined,

  initialize: (meta) => {
    if (get().methodId === meta.id && get().status !== "idle") return;
    set({
      methodId: meta.id,
      inputs: defaultInputs(meta),
      status: "idle",
      response: undefined,
      error: undefined,
    });
  },

  setInput: (key, value) =>
    set((state) => ({ inputs: { ...state.inputs, [key]: value } })),

  loadExample: (inputs, meta) =>
    set({
      methodId: meta.id,
      inputs: { ...defaultInputs(meta), ...inputs },
      status: "idle",
      response: undefined,
      error: undefined,
    }),

  run: async (meta) => {
    set({ status: "loading", error: undefined, response: undefined });
    try {
      const response = await api.solve(meta.id, get().inputs);
      set({ status: "done", response, error: undefined });
    } catch (error) {
      set({
        status: "error",
        error: error instanceof ApiError ? error : new ApiError("Solving failed unexpectedly."),
        response: undefined,
      });
    }
  },

  clearResult: () => set({ status: "idle", response: undefined, error: undefined }),
}));
