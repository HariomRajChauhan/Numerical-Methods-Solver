/**
 * TypeScript mirror of the backend response contract.
 * Source of truth: backend/app/core/models.py — keep in sync.
 */

export type ChapterId =
  | "ch1_nonlinear"
  | "ch2_linear"
  | "ch3_interpolation"
  | "ch4_diff_integration"
  | "ch5_ode"
  | "ch6_pde";

export interface ChapterInfo {
  id: ChapterId;
  number: number;
  title: string;
  description: string;
  method_count: number;
  available_count: number;
}

export type FieldType =
  | "function"
  | "number"
  | "integer"
  | "boolean"
  | "text"
  | "select"
  | "vector"
  | "data_points"
  | "matrix"
  | "tolerance"
  | "max_iterations"
  | "precision";

export interface SelectOption {
  value: string;
  label: string;
}

export interface InputField {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  default: unknown;
  help: string;
  placeholder: string;
  min: number | null;
  max: number | null;
  variable: string | null;
  rows: number | null;
  cols: number | null;
  options: SelectOption[];
}

export interface MethodExample {
  name: string;
  inputs: Record<string, unknown>;
  description: string;
}

export interface LabeledLatex {
  label: string;
  latex: string;
}

export type MethodStatus = "available" | "coming_soon";

export interface MethodMeta {
  id: string;
  chapter: ChapterId;
  /** Variables the method allows (drives the keypad variable tab). */
  variables: string[];
  name: string;
  status: MethodStatus;
  summary: string;
  theory: string;
  pseudocode: string;
  formulas: LabeledLatex[];
  input_schema: InputField[];
  examples: MethodExample[];
  chapter_title: string;
  chapter_number: number;
}

export interface MethodCatalog {
  chapters: ChapterInfo[];
  methods: MethodMeta[];
}

export type SolveStatus = "converged" | "diverged" | "max_iter" | "failed";

export interface Step {
  title: string;
  latex: string;
  note: string;
}

export interface DataTable {
  title: string;
  columns: string[];
  rows: (string | number | boolean | null)[][];
}

export type PlotTrace = Record<string, unknown>;

export interface PlotPayload {
  traces: PlotTrace[];
  layout: Record<string, unknown>;
}

export interface ErrorInfo {
  absolute: number | null;
  relative_percent: number | null;
  order_of_convergence: number | null;
}

export interface SolveResponse {
  method: string;
  status: SolveStatus;
  result: Record<string, unknown>;
  steps: Step[];
  tables: DataTable[];
  plot: PlotPayload;
  errors: ErrorInfo;
  warnings: string[];
  pseudocode: string;
  python_source: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}
