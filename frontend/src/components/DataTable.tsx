import { useMemo } from "react";

import type { DataTable as DataTableType } from "../types/api";
import { downloadText, slugify } from "../utils/download";
import { formatCell, tableToCsv } from "../utils/format";
import { ui } from "../utils/ui";
import { CopyButton } from "./CopyButton";

interface DataTableProps {
  table: DataTableType;
  /** Decimal places used when rendering numeric cells. */
  precision?: number;
}

/** Iteration table: sticky header, copy/CSV export, highlighted final row. */
export function DataTable({ table, precision = 6 }: DataTableProps) {
  const csv = useMemo(() => tableToCsv(table, precision), [table, precision]);

  return (
    <section className={`overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-2.5 dark:border-slate-800">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{table.title}</h3>
        <div className="flex items-center gap-1">
          <CopyButton text={csv} label="Copy CSV" />
          <button
            type="button"
            onClick={() => downloadText(`${slugify(table.title)}.csv`, csv, "text/csv")}
            className={ui.btnGhost}
          >
            ⤓ Download CSV
          </button>
        </div>
      </header>
      <div className="max-h-[28rem] overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-100 text-left dark:bg-slate-800">
            <tr>
              {table.columns.map((column) => (
                <th
                  key={column}
                  scope="col"
                  className="whitespace-nowrap px-3 py-2 font-semibold text-slate-700 dark:text-slate-200"
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
                  className={`border-t border-slate-100 dark:border-slate-800 ${
                    isLast
                      ? "bg-emerald-50/70 font-medium dark:bg-emerald-950/30"
                      : "odd:bg-white even:bg-slate-50/60 dark:odd:bg-slate-900 dark:even:bg-slate-900/40"
                  }`}
                >
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className="whitespace-nowrap px-3 py-1.5 font-mono text-xs text-slate-700 dark:text-slate-300"
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
    </section>
  );
}
