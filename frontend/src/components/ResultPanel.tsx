import type { SolveResponse } from "../types/api";
import { formatResultValue } from "../utils/format";
import { ui } from "../utils/ui";
import { SolveStatusBadge } from "./StatusBadge";
import { Icon } from "./ui/Icon";

interface ResultPanelProps {
  response: SolveResponse;
  precision?: number;
}

function humanize(key: string): string {
  const label = key.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** "Answer" tab: highlighted final value, all result fields and error metrics. */
export function ResultPanel({ response, precision = 6 }: ResultPanelProps) {
  const { result, errors } = response;
  const resultEntries = Object.entries(result);
  const [primary, ...rest] = resultEntries;

  const metrics = [
    { label: "Absolute error", value: errors.absolute },
    {
      label: "Relative error",
      value:
        errors.relative_percent === null || errors.relative_percent === undefined
          ? null
          : `${errors.relative_percent} %`,
    },
    { label: "Order of convergence", value: errors.order_of_convergence },
  ].filter((metric) => metric.value !== null && metric.value !== undefined);

  return (
    <div className="animate-fade-in space-y-4">
      {response.warnings.length > 0 && (
        <ul
          aria-live="polite"
          className="space-y-1.5 rounded-2xl border border-amber-200/80 bg-amber-50/90 p-3.5 text-sm text-amber-800 dark:border-amber-400/20 dark:bg-amber-500/[0.07] dark:text-amber-200"
        >
          {response.warnings.map((warning) => (
            <li key={warning} className="flex items-start gap-2">
              <Icon name="alert" size={15} className="mt-0.5 shrink-0" />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      )}

      {primary ? (
        <section className="relative overflow-hidden rounded-2xl border border-indigo-200/70 bg-gradient-to-br from-indigo-50/90 via-white to-white p-5 dark:border-indigo-400/20 dark:from-indigo-500/[0.07] dark:via-slate-900/60 dark:to-slate-900/60">
          <div
            aria-hidden="true"
            className="absolute -right-10 -top-12 h-36 w-36 rounded-full bg-indigo-500/10 blur-2xl"
          />
          <div className="relative flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-indigo-600 dark:text-indigo-300">
              {humanize(primary[0])}
            </p>
            <SolveStatusBadge status={response.status} />
          </div>
          <p className="relative mt-2 break-all font-mono text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
            {formatResultValue(primary[1], precision)}
          </p>
        </section>
      ) : (
        <section className={`flex flex-wrap items-center justify-between gap-2 p-4 ${ui.card}`}>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No final value was produced.
          </p>
          <SolveStatusBadge status={response.status} />
        </section>
      )}

      {rest.length > 0 && (
        <section className={`p-4 ${ui.card}`}>
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            All results
          </h3>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {rest.map(([key, value]) => (
              <div
                key={key}
                className="rounded-xl border border-slate-200/70 bg-slate-50/70 px-3 py-2.5 dark:border-white/[0.06] dark:bg-white/[0.03]"
              >
                <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  {humanize(key)}
                </dt>
                <dd className="mt-0.5 break-all font-mono text-sm font-medium text-slate-800 dark:text-slate-100">
                  {formatResultValue(value, precision)}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {metrics.length > 0 && (
        <section className={`p-4 ${ui.card}`}>
          <div className="flex items-center gap-2">
            <span className={`${ui.iconBox} h-7 w-7`}>
              <Icon name="chart" size={14} />
            </span>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Error &amp; convergence
            </h3>
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-3">
            {metrics.map((metric) => (
              <div
                key={metric.label}
                className="rounded-xl border border-slate-200/70 bg-slate-50/70 px-3 py-2.5 dark:border-white/[0.06] dark:bg-white/[0.03]"
              >
                <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  {metric.label}
                </dt>
                <dd className="mt-0.5 font-mono text-sm text-slate-800 dark:text-slate-100">
                  {typeof metric.value === "number"
                    ? formatResultValue(metric.value, precision)
                    : metric.value}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
    </div>
  );
}
