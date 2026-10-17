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

  function focusCell(row: number, col: number): void {
    const element = cellMap.current.get(`${row}:${col}`);
    element?.focus();
    element?.select();
  }

  const cellMap = useRef(new Map<string, HTMLInputElement>());

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
                  className="w-20 rounded-md border border-slate-300 bg-white px-2 py-1 text-right font-mono text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
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
