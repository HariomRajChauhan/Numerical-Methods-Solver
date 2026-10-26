import { useMemo } from "react";

import type { DataTable as DataTableType } from "../types/api";
import { downloadText, slugify } from "../utils/download";
import { formatCell, tableToCsv } from "../utils/format";
import { ui } from "../utils/ui";
import { CopyButton } from "./CopyButton";
import { Icon } from "./ui/Icon";

interface DataTableProps {
  table: DataTableType;
  /** Decimal places used when rendering numeric cells. */
  precision?: number;
}

/** Iteration table: sticky header, copy/CSV export, highlighted final row. */
export function DataTable({ table, precision = 6 }: DataTableProps) {
  const csv = useMemo(() => tableToCsv(table, precision), [table, precision]);

  return (
    <section className={`animate-fade-in overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 px-4 py-3 dark:border-white/[0.07]">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name="table" size={14} />
          </span>
          <h3 className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
            {table.title}
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <CopyButton text={csv} label="Copy CSV" />
          <button
            type="button"
            onClick={() => downloadText(`${slugify(table.title)}.csv`, csv, "text/csv")}
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
        className="max-h-[30rem] overflow-auto scroll-slim focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500"
      >
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-100/95 text-left backdrop-blur dark:bg-slate-800/95">
            <tr>
              {table.columns.map((column) => (
                <th
                  key={column}
                  scope="col"
                  className="whitespace-nowrap px-3.5 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => {
              const isLast = rowIndex === table.rows.length - 1;
              return (
                <tr
                  key={rowIndex}
                  className={`border-t border-slate-100 dark:border-white/[0.05] ${
                    isLast
                      ? "bg-emerald-50/70 font-medium dark:bg-emerald-500/[0.08]"
                      : "odd:bg-white even:bg-slate-50/50 dark:odd:bg-transparent dark:even:bg-white/[0.02]"
                  }`}
                >
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className={`whitespace-nowrap px-3.5 py-2 font-mono text-xs tabular-nums text-slate-700 dark:text-slate-300 ${
                        typeof cell === "number" ? "text-right" : ""
                      }`}
                    >
                      {formatCell(cell, precision)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between gap-2 border-t border-slate-100 px-4 py-2 text-[11px] text-slate-600 dark:border-white/[0.06] dark:text-slate-400">
        <span>
          {table.rows.length} row{table.rows.length === 1 ? "" : "s"}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Final row highlighted
        </span>
      </footer>
    </section>
  );
}
