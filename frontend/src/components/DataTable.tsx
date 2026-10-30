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
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollEdge, setScrollEdge] = useState({ left: false, right: false });

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    function updateShadow(): void {
      if (!el) return;
      setScrollEdge({
        left: el.scrollLeft > 2,
        right: el.scrollLeft + el.clientWidth < el.scrollWidth - 2,
      });
    }
    updateShadow();
    el.addEventListener("scroll", updateShadow, { passive: true });
    const ro = new ResizeObserver(updateShadow);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", updateShadow);
      ro.disconnect();
    };
  }, []);

  /** Copy a single row as tab-separated text. */
  function copyRow(rowIndex: number): void {
    const row = table.rows[rowIndex];
    if (!row) return;
    const text = row.map((cell) => formatCell(cell, precision)).join("\t");
    void copyText(text);
    toast({ tone: "success", title: "Row copied", duration: 2000 });
  }

  return (
    <section data-testid="data-table" className={`animate-fade-in overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name="table" size={14} />
          </span>
          <h3 className="truncate text-sm font-semibold text-[color:var(--color-text)]">{table.title}</h3>
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

      <div className="relative">
        {/* Edge shadows */}
        {scrollEdge.left && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 left-0 top-0 z-20 w-4 bg-gradient-to-r from-[color:var(--color-surface)] to-transparent"
          />
        )}
        {scrollEdge.right && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 right-0 top-0 z-20 w-4 bg-gradient-to-l from-[color:var(--color-surface)] to-transparent"
          />
        )}
        <div
          ref={scrollRef}
          role="region"
          aria-label={`${table.title} table`}
          tabIndex={0}
          className="max-h-[32rem] overflow-auto scroll-slim focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[color:var(--color-accent)]"
        >
          <table className="w-full border-separate border-spacing-0 text-left">
            <thead>
              <tr>
                {table.columns.map((column, columnIndex) => (
                  <th
                    key={column}
                    scope="col"
                    className={`sticky top-0 z-20 whitespace-nowrap border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] text-2xs font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)] ${HEAD_PADDING[density]} ${
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
                  ? "bg-[color:var(--color-success-soft)]"
                  : rowIndex % 2 === 1
                    ? "bg-[color:var(--color-surface-2)]"
                    : "bg-[color:var(--color-surface)]";
                return (
                  <tr
                    key={rowIndex}
                    className={`${rowTone} group/row`}
                    onDoubleClick={() => copyRow(rowIndex)}
                    title="Double-click to copy row"
                  >
                    {row.map((cell, cellIndex) => {
                      const numeric = typeof cell === "number";
                      const text = formatCell(cell, precision);
                      return (
                        <td
                          key={cellIndex}
                          className={`border-b border-[color:color-mix(in_oklab,var(--color-border)_70%,transparent)] whitespace-nowrap align-middle font-mono tabular-nums ${CELL_PADDING[density]} ${
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
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-[color:var(--color-border)] px-4 py-2 text-2xs text-[color:var(--color-text-muted)]">
        <span>
          {table.rows.length} row{table.rows.length === 1 ? "" : "s"} · sticky header and first
          column
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-[color:var(--color-success)]" />
            Final row highlighted
          </span>
          <span aria-hidden="true" className="h-3 w-px bg-[color:var(--color-border)]" />
          <div
            role="group"
            aria-label="Table density"
            className="inline-flex items-center rounded-[var(--radius-1)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-0.5"
          >
            {(["compact", "comfortable"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={density === value}
                onClick={() => setDensity(value)}
                className={`rounded-[calc(var(--radius-1)-2px)] px-2 py-0.5 font-medium capitalize transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] ${
                  density === value
                    ? "bg-[color:var(--color-surface)] text-[color:var(--color-text)] shadow-sm"
                    : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]"
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
      className={`group/cell flex w-full items-center gap-1.5 rounded-sm text-left font-mono tabular-nums transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[color:var(--color-accent)] ${
        numeric ? "justify-end text-right" : ""
      } ${first ? "font-semibold text-[color:var(--color-text)]" : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]"} ${
        emphasized ? "text-[color:var(--color-text)]" : ""
      }`}
    >
      <span className="truncate">{text}</span>
      <Icon
        name={copied ? "check" : "copy"}
        size={11}
        className={`shrink-0 transition duration-150 ${
          copied
            ? "text-[color:var(--color-success)] opacity-100"
            : "text-[color:var(--color-text-subtle)] opacity-0 group-hover/cell:opacity-100 group-focus-visible/cell:opacity-100"
        }`}
      />
    </button>
  );
}
