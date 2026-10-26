import { useEffect, useMemo, useRef, useState } from "react";

import { toast } from "../store/toast";
import type { DataTable as DataTableType } from "../types/api";
import { copyText, downloadText, slugify } from "../utils/download";
import { formatCell, tableToCsv } from "../utils/format";
import { ui } from "../utils/ui";
import { CopyButton } from "./CopyButton";
import { Icon } from "./ui/Icon";

interface DataTableProps {
  table: DataTableType;
  /** Decimal places used when rendering numeric cells. */
  precision?: number;
}

type Density = "compact" | "comfortable";

const CELL_PADDING: Record<Density, string> = {
  compact: "px-2 py-1 text-2xs",
  comfortable: "px-3 py-2 text-xs",
};

const HEAD_PADDING: Record<Density, string> = {
  compact: "px-2 py-1.5",
  comfortable: "px-3 py-2.5",
};

/** Iteration table: sticky axes, copyable cells, density control and CSV export. */
export function DataTable({ table, precision = 6 }: DataTableProps) {
  const [density, setDensity] = useState<Density>("comfortable");
  const csv = useMemo(() => tableToCsv(table, precision), [table, precision]);

  return (
    <section className={`animate-fade-in overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name="table" size={14} />
          </span>
          <h3 className="truncate text-sm font-semibold text-ink">{table.title}</h3>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <CopyButton text={csv} label="Copy table" />
          <button
            type="button"
            onClick={() => {
              downloadText(`${slugify(table.title)}.csv`, csv, "text/csv");
              toast({
                tone: "success",
                title: "Table downloaded",
                message: `${table.title} saved as CSV.`,
                duration: 3000,
              });
            }}
            className={ui.btnGhost}
          >
            <Icon name="download" size={13} />
            Download CSV
          </button>
        </div>
      </header>

      <div
        role="region"
        aria-label={`${table.title} table`}
        tabIndex={0}
        className="max-h-[32rem] overflow-auto scroll-slim focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-500"
      >
        <table className="w-full border-separate border-spacing-0 text-left">
          <thead>
            <tr>
              {table.columns.map((column, columnIndex) => (
                <th
                  key={column}
                  scope="col"
                  className={`sticky top-0 z-20 whitespace-nowrap border-b border-line bg-surface-muted text-2xs font-semibold uppercase tracking-wide text-ink-muted ${HEAD_PADDING[density]} ${
                    columnIndex === 0 ? "left-0 z-30" : ""
                  }`}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => {
              const isLast = rowIndex === table.rows.length - 1;
              const rowTone = isLast
                ? "bg-success-soft"
                : rowIndex % 2 === 1
                  ? "bg-surface-muted"
                  : "bg-surface";
              return (
                <tr key={rowIndex} className={rowTone}>
                  {row.map((cell, cellIndex) => {
                    const numeric = typeof cell === "number";
                    const text = formatCell(cell, precision);
                    return (
                      <td
                        key={cellIndex}
                        className={`border-b border-line/70 whitespace-nowrap align-middle font-mono tabular-nums ${CELL_PADDING[density]} ${
                          cellIndex === 0 ? "sticky left-0 z-10 bg-inherit" : ""
                        } ${numeric ? "text-right" : ""}`}
                      >
                        <CellCopy
                          text={text}
                          column={table.columns[cellIndex] ?? `column ${cellIndex + 1}`}
                          numeric={numeric}
                          first={cellIndex === 0}
                          emphasized={isLast}
                        />
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2 text-2xs text-ink-muted">
        <span>
          {table.rows.length} row{table.rows.length === 1 ? "" : "s"} · sticky header and first
          column
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-success" />
            Final row highlighted
          </span>
          <span aria-hidden="true" className="h-3 w-px bg-line" />
          <div
            role="group"
            aria-label="Table density"
            className="inline-flex items-center rounded-control border border-line bg-surface-muted p-0.5"
          >
            {(["compact", "comfortable"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={density === value}
                onClick={() => setDensity(value)}
                className={`rounded-[calc(var(--radius-control)-2px)] px-2 py-0.5 font-medium capitalize transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${
                  density === value
                    ? "bg-surface text-ink shadow-sm"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {value === "compact" ? "Compact" : "Comfortable"}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </section>
  );
}

interface CellCopyProps {
  text: string;
  column: string;
  numeric: boolean;
  first: boolean;
  emphasized: boolean;
}

/** A cell that can be copied with one click, while remaining readable as text. */
function CellCopy({ text, column, numeric, first, emphasized }: CellCopyProps) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timerRef.current), []);

  async function handleCopy(): Promise<void> {
    if (!(await copyText(text))) return;
    setCopied(true);
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      aria-label={copied ? `${column} value copied` : `Copy ${column} value ${text}`}
      title={copied ? "Copied" : `Copy ${column}`}
      className={`group/cell flex w-full items-center gap-1.5 rounded-sm text-left font-mono tabular-nums transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-500 ${
        numeric ? "justify-end text-right" : ""
      } ${first ? "font-semibold text-ink" : "text-ink-muted hover:text-ink"} ${
        emphasized ? "text-ink" : ""
      }`}
    >
      <span className="truncate">{text}</span>
      <Icon
        name={copied ? "check" : "copy"}
        size={11}
        className={`shrink-0 transition duration-150 ${
          copied
            ? "text-success opacity-100"
            : "text-ink-subtle opacity-0 group-hover/cell:opacity-100 group-focus-visible/cell:opacity-100"
        }`}
      />
    </button>
  );
}
