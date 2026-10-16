import type { InputField } from "../types/api";
import { ui } from "../utils/ui";

interface MatrixInputProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

function toMatrix(value: unknown, rows: number, cols: number): string[][] {
  if (Array.isArray(value) && value.length > 0 && Array.isArray(value[0])) {
    return (value as unknown[][]).map((row) => row.map((cell) => String(cell ?? "")));
  }
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => "0"));
}

/** Resizable grid of numeric cells for matrix inputs. */
export function MatrixInput({ field, value, onChange, error }: MatrixInputProps) {
  const rows = field.rows ?? 3;
  const cols = field.cols ?? rows + 1;
  const matrix = toMatrix(value, rows, cols);
  const width = matrix[0]?.length ?? 0;

  function emit(next: string[][]): void {
    onChange(next);
  }

  function setCell(rowIndex: number, colIndex: number, cell: string): void {
    const next = matrix.map((row) => [...row]);
    next[rowIndex][colIndex] = cell;
    emit(next);
  }

  function addRow(): void {
    emit([...matrix, Array.from({ length: width }, () => "0")]);
  }

  function removeRow(): void {
    if (matrix.length > 1) emit(matrix.slice(0, -1));
  }

  function addColumn(): void {
    emit(matrix.map((row) => [...row, "0"]));
  }

  function removeColumn(): void {
    if (width > 1) emit(matrix.map((row) => row.slice(0, -1)));
  }

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label className={ui.label}>{field.label}</label>
        <div className="flex gap-1">
          <button type="button" onClick={addRow} className={ui.btnGhost} title="Add row">
            + Row
          </button>
          <button type="button" onClick={removeRow} className={ui.btnGhost} title="Remove row">
            − Row
          </button>
          <button type="button" onClick={addColumn} className={ui.btnGhost} title="Add column">
            + Col
          </button>
          <button type="button" onClick={removeColumn} className={ui.btnGhost} title="Remove column">
            − Col
          </button>
        </div>
      </div>
      <div
        className={`inline-block overflow-x-auto rounded-lg border p-2 ${
          error ? "border-rose-400" : "border-slate-200 dark:border-slate-800"
        }`}
      >
        {matrix.map((row, rowIndex) => (
          <div key={rowIndex} className="flex gap-1.5 py-0.5">
            {row.map((cell, colIndex) => (
              <input
                key={colIndex}
                aria-label={`${field.label} row ${rowIndex + 1} column ${colIndex + 1}`}
                type="text"
                inputMode="decimal"
                value={cell}
                onChange={(event) => setCell(rowIndex, colIndex, event.target.value)}
                className="w-20 rounded-md border border-slate-300 bg-white px-2 py-1 text-right font-mono text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              />
            ))}
          </div>
        ))}
      </div>
      {field.help && <p className={ui.help}>{field.help}</p>}
      {error && (
        <p role="alert" className={ui.error}>
          {error}
        </p>
      )}
    </div>
  );
}
