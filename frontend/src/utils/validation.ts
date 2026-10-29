import type { FieldType, InputField, MethodMeta } from "../types/api";

const NUMERIC_TYPES = new Set<FieldType>([
  "number",
  "integer",
  "tolerance",
  "max_iterations",
  "precision",
]);

function isBlank(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

function asNumber(value: unknown): number {
  if (typeof value === "number") return value;
  return Number(String(value ?? "").trim());
}

function parseNumberList(value: unknown): number[] | null {
  const parts = String(value ?? "")
    .split(/[,\s;]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length === 0) return null;
  const numbers = parts.map(Number);
  return numbers.every(Number.isFinite) ? numbers : null;
}

function parsePointList(value: unknown): [number, number][] | null {
  const chunks = String(value ?? "")
    .split(/[;\n]+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  if (chunks.length === 0) return null;

  const points: [number, number][] = [];
  for (const chunk of chunks) {
    const parts = chunk.split(/[,\s]+/).filter(Boolean);
    if (parts.length !== 2) return null;
    const x = Number(parts[0]);
    const y = Number(parts[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    points.push([x, y]);
  }
  return points;
}

function validateMatrix(value: unknown): string | null {
  if (!Array.isArray(value) || value.length === 0) return "Enter at least one matrix row.";
  const rows = value as unknown[];
  if (rows.some((row) => !Array.isArray(row) || row.length === 0)) {
    return "Every matrix row needs at least one value.";
  }
  const cells = rows.flatMap((row) => row as unknown[]);
  if (
    cells.some((cell) => {
      const text = String(cell ?? "").trim();
      return text === "" || !Number.isFinite(Number(text));
    })
  ) {
    return "Every matrix cell must contain a number.";
  }
  return null;
}

function rangeError(field: InputField, value: number): string | null {
  if (field.min !== null && value < field.min) {
    return `${field.label} must be at least ${field.min}.`;
  }
  if (field.max !== null && value > field.max) {
    return `${field.label} must be at most ${field.max}.`;
  }
  return null;
}

function validateField(field: InputField, value: unknown): string | undefined {
  if (field.type === "boolean") return undefined;

  if (isBlank(value)) {
    return field.required ? `${field.label} is required.` : undefined;
  }

  if (NUMERIC_TYPES.has(field.type)) {
    const number = asNumber(value);
    if (!Number.isFinite(number)) return `${field.label} must be a number.`;
    if (field.type === "integer" && !Number.isInteger(number)) {
      return `${field.label} must be a whole number.`;
    }
    if (field.type === "max_iterations" && (!Number.isInteger(number) || number < 1)) {
      return `${field.label} must be a whole number of at least 1.`;
    }
    if (field.type === "precision" && (!Number.isInteger(number) || number < 0)) {
      return `${field.label} must be a whole number of 0 or more.`;
    }
    if (field.type === "tolerance" && number <= 0) {
      return `${field.label} must be greater than zero.`;
    }
    return rangeError(field, number) ?? undefined;
  }

  if (field.type === "select") {
    const selected = String(value);
    if (field.options.length > 0 && !field.options.some((option) => option.value === selected)) {
      return `Choose a valid option for ${field.label.toLowerCase()}.`;
    }
    return undefined;
  }

  if (field.type === "vector") {
    return parseNumberList(value) ? undefined : "Enter a list of numbers separated by commas.";
  }

  if (field.type === "data_points") {
    return parsePointList(value)
      ? undefined
      : "Use one x,y pair per line (for example 0,1 then 1,2).";
  }

  if (field.type === "matrix") {
    return validateMatrix(value) ?? undefined;
  }

  return undefined;
}

/** Validate the current form values against a method's schema before submitting. */
export function validateInputs(
  meta: MethodMeta,
  inputs: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of meta.input_schema) {
    const error = validateField(field, inputs[field.key]);
    if (error) errors[field.key] = error;
  }
  return errors;
}
