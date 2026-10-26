import { useRef, useState, type KeyboardEvent } from "react";

import type { InputField } from "../types/api";
import { ui } from "../utils/ui";
import { KeypadToggle } from "./fields/MathKeypad";
import { NumericKeypad } from "./fields/NumericKeypad";
import { NUMERIC_KEYPAD_STORAGE_KEY, useKeypadInput } from "./fields/useKeypadInput";

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

  const activeRef = useRef<HTMLInputElement | null>(null);
  const [active, setActive] = useState<{ row: number; col: number } | null>(null);

  const activeValue = active ? (matrix[active.row]?.[active.col] ?? "") : "";
  const keypad = useKeypadInput(
    activeRef,
    activeValue,
    (next) => {
      if (active) setCell(active.row, active.col, next);
    },
    NUMERIC_KEYPAD_STORAGE_KEY,
  );

  function emit(next: string[][]): void {
    onChange(next);
  }

  function setCell(rowIndex: number, colIndex: number, cell: string): void {
    const next = matrix.map((row) => [...row]);
    next[rowIndex][colIndex] = cell;
    onChange(next);
  }

  const cellMap = useRef(new Map<string, HTMLInputElement>());

  function focusCell(row: number, col: number): void {
    const element = cellMap.current.get(`${row}:${col}`);
    element?.focus();
    element?.select();
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLInputElement>,
    row: number,
    col: number,
  ): void {
    const element = event.currentTarget;
    const atStart = element.selectionStart === 0 && element.selectionEnd === 0;
    const atEnd =
      element.selectionStart === element.value.length &&
      element.selectionEnd === element.value.length;
    switch (event.key) {
      case "ArrowUp":
        event.preventDefault();
        focusCell(row - 1, col);
        break;
      case "ArrowDown":
      case "Enter":
        event.preventDefault();
        focusCell(row + 1, col);
        break;
      case "ArrowLeft":
        if (atStart) {
          event.preventDefault();
          focusCell(row, col - 1);
        }
        break;
      case "ArrowRight":
        if (atEnd) {
          event.preventDefault();
          focusCell(row, col + 1);
        }
        break;
      default:
        break;
    }
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
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className={ui.label}>{field.label}</span>
          <p className="mt-0.5 text-[11px] text-slate-600 dark:text-slate-400">
            {matrix.length} × {width} matrix · use arrow keys to move between cells
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" onClick={addRow} className={ui.btnGhost} title="Add row">
            + Row
          </button>
          <button type="button" onClick={removeRow} className={ui.btnGhost} title="Remove row">
            − Row
          </button>
          <span aria-hidden="true" className="mx-0.5 h-4 w-px bg-slate-200 dark:bg-white/10" />
          <button type="button" onClick={addColumn} className={ui.btnGhost} title="Add column">
            + Col
          </button>
          <button
            type="button"
            onClick={removeColumn}
            className={ui.btnGhost}
            title="Remove column"
          >
            − Col
          </button>
        </div>
      </div>

      <div
        className={`inline-block max-w-full overflow-x-auto rounded-xl border p-3 scroll-slim ${
          error
            ? "border-rose-400 dark:border-rose-500/70"
            : "border-slate-200/80 bg-slate-50/60 dark:border-white/[0.07] dark:bg-white/[0.02]"
        }`}
      >
        {matrix.map((row, rowIndex) => (
          <div key={rowIndex} className="flex gap-1.5 py-0.5">
            {row.map((cell, colIndex) => {
              const cellKey = `${rowIndex}:${colIndex}`;
              return (
                <input
                  key={colIndex}
                  ref={(element) => {
                    if (element) cellMap.current.set(cellKey, element);
                    else cellMap.current.delete(cellKey);
                  }}
                  aria-label={`${field.label} row ${rowIndex + 1} column ${colIndex + 1}`}
                  type="text"
                  inputMode="decimal"
                  value={cell}
                  onFocus={(event) => {
                    activeRef.current = event.currentTarget;
                    setActive({ row: rowIndex, col: colIndex });
                  }}
                  onChange={(event) => setCell(rowIndex, colIndex, event.target.value)}
                  onKeyDown={(event) => handleKeyDown(event, rowIndex, colIndex)}
                  className="h-9 w-[4.75rem] rounded-lg border border-slate-300/90 bg-white px-2 text-right font-mono text-sm text-slate-800 shadow-sm transition focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 dark:border-white/10 dark:bg-slate-950/50 dark:text-slate-100 dark:focus:border-indigo-400"
                />
              );
            })}
          </div>
        ))}
      </div>

      <div className="mt-1.5">
        <KeypadToggle open={keypad.show} onToggle={keypad.toggle} />
      </div>
      {keypad.show && <NumericKeypad onAction={keypad.handleAction} />}
      {field.help && <p className={ui.help}>{field.help}</p>}
      {error && (
        <p role="alert" className={ui.error}>
          {error}
        </p>
      )}
    </div>
  );
}
