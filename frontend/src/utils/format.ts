import type { DataTable } from "../types/api";

/** Human-readable formatting for solver results and table cells. */

export function formatNumber(value: number, precision = 6): string {
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  if (magnitude >= 1e6 || magnitude < 1e-4) {
    return value.toExponential(Math.min(precision, 6));
  }
  const fixed = value.toFixed(precision);
  return fixed.includes(".") ? fixed.replace(/\.?0+$/, "") : fixed;
}

export function formatCell(value: unknown, precision = 6): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return formatNumber(value, precision);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export function formatResultValue(value: unknown, precision = 6): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return formatNumber(value, precision);
  if (Array.isArray(value)) {
    return value.every((item) => item === null || item === undefined || typeof item !== "object")
      ? `[${value.map((item) => formatCell(item, precision)).join(", ")}]`
      : JSON.stringify(value);
  }
  if (typeof value === "object") return JSON.stringify(value);
  return formatCell(value, precision);
}

/** Turn a solver table into CSV text (RFC-4180-ish: quote fields with commas). */
export function tableToCsv(table: DataTable, precision = 6): string {
  const escape = (text: string): string =>
    /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  const lines = [
    table.columns.map((column) => escape(column)).join(","),
    ...table.rows.map((row) => row.map((cell) => escape(formatCell(cell, precision))).join(",")),
  ];
  return lines.join("\n");
}
