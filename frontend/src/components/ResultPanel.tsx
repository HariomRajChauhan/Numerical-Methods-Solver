import type { SolveResponse } from "../types/api";
import { formatResultValue } from "../utils/format";
import { ui } from "../utils/ui";
import { SolveStatusBadge } from "./StatusBadge";

interface ResultPanelProps {
  response: SolveResponse;
  precision?: number;
}

/** "Answer" tab: final named values, error metrics and warnings. */
export function ResultPanel({ response, precision = 6 }: ResultPanelProps) {
  const { result, errors } = response;
  const resultEntries = Object.entries(result);
  const errorEntries = [
    ["Absolute error", errors.absolute],
    ["Relative error", errors.relative_percent === null ? null : `${errors.relative_percent} %`],
    ["Order of convergence", errors.order_of_convergence],
  ] as const;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <SolveStatusBadge status={response.status} />
        {response.status === "max_iter" && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            The tolerance was not reached within the iteration limit.
          </span>
        )}
      </div>

      {response.warnings.length > 0 && (
        <ul className="space-y-1 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
          {response.warnings.map((warning) => (
            <li key={warning}>⚠ {warning}</li>
          ))}
        </ul>
      )}

      <section className={`p-4 ${ui.card}`}>
        <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Result</h3>
        {resultEntries.length === 0 ? (
          <p className="text-sm text-slate-500">No final value was produced.</p>
        ) : (
          <dl className="grid gap-3 sm:grid-cols-2">
            {resultEntries.map(([key, value]) => (
              <div key={key} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950/60">
                <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {key.replace(/_/g, " ")}
                </dt>
                <dd className="mt-0.5 break-all font-mono text-sm font-medium text-slate-900 dark:text-slate-100">
                  {formatResultValue(value, precision)}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      {errorEntries.some(([, value]) => value !== null && value !== undefined) && (
        <section className={`p-4 ${ui.card}`}>
          <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
            Error &amp; convergence
          </h3>
          <dl className="grid gap-3 sm:grid-cols-3">
            {errorEntries
              .filter(([, value]) => value !== null && value !== undefined)
              .map(([label, value]) => (
                <div key={label} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950/60">
                  <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    {label}
                  </dt>
                  <dd className="mt-0.5 font-mono text-sm text-slate-900 dark:text-slate-100">
                    {typeof value === "number" ? formatResultValue(value, precision) : value}
                  </dd>
                </div>
              ))}
          </dl>
        </section>
      )}
    </div>
  );
}
