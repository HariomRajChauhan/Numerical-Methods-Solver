import type { SolveResponse } from "../types/api";
import { formatResultValue } from "../utils/format";
import { ui } from "../utils/ui";
import { SolveStatusBadge } from "./StatusBadge";
import { Icon } from "./ui/Icon";

interface ResultHeaderProps {
  response: SolveResponse;
  precision?: number;
  methodName?: string;
}

function humanize(key: string): string {
  const label = key.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/**
 * Result header: headline answer, status chip, stat row,
 * plain-language summary, warnings as alerts, and a result footer.
 */
export function ResultHeader({
  response,
  precision = 6,
  methodName,
}: ResultHeaderProps) {
  const { result, errors, status } = response;
  const resultEntries = Object.entries(result);
  const [primary, ...rest] = resultEntries;

  const stats: { label: string; value: string }[] = [];
  if (response.steps.length > 0) stats.push({ label: "Steps", value: String(response.steps.length) });
  if (response.tables.length > 0) {
    const totalRows = response.tables.reduce((sum, t) => sum + t.rows.length, 0);
    stats.push({ label: "Iterations", value: String(totalRows) });
  }
  if (errors.absolute !== null && errors.absolute !== undefined) {
    stats.push({ label: "|ε|", value: formatResultValue(errors.absolute, precision) });
  }
  if (errors.relative_percent !== null && errors.relative_percent !== undefined) {
    stats.push({ label: "rel ε", value: `${errors.relative_percent}%` });
  }
  if (errors.order_of_convergence !== null && errors.order_of_convergence !== undefined) {
    stats.push({ label: "Order", value: formatResultValue(errors.order_of_convergence, 2) });
  }

  const summaryText = buildSummary(response, precision, methodName);

  return (
    <div className="animate-fade-in space-y-4">
      {/* Warnings */}
      {response.warnings.length > 0 && (
        <ul
          aria-live="polite"
          className="space-y-2 rounded-[var(--radius-3)] border border-[color:color-mix(in_oklab,var(--color-warning)_30%,transparent)] bg-[color:var(--color-warning-soft)] p-4 text-sm"
        >
          {response.warnings.map((warning) => (
            <li key={warning} className="flex items-start gap-2.5">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[color:color-mix(in_oklab,var(--color-warning)_15%,transparent)]">
                <Icon name="alert" size={14} className="text-[color:var(--color-warning)]" />
              </span>
              <div className="min-w-0 flex-1">
                <span className="font-medium text-[color:var(--color-warning)]">{warning}</span>
                <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
                  Check your input parameters and try adjusting tolerance or iteration limits.
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Headline answer */}
      {primary ? (
        <section
          data-testid="result-headline"
          className="relative overflow-hidden rounded-[var(--radius-3)] border border-[color:color-mix(in_oklab,var(--color-accent)_30%,transparent)] bg-gradient-to-br from-[color:var(--color-accent-soft)] via-[color:var(--color-surface)] to-[color:var(--color-surface)] p-5"
        >
          <div
            aria-hidden="true"
            className="absolute -right-10 -top-12 h-36 w-36 rounded-full bg-[color:color-mix(in_oklab,var(--color-accent)_10%,transparent)] blur-2xl"
          />
          <div className="relative flex flex-wrap items-center justify-between gap-2">
            <p className="text-2xs font-semibold uppercase tracking-[0.16em] text-[color:var(--color-accent)]">
              {humanize(primary[0])}
            </p>
            <SolveStatusBadge status={status} />
          </div>
          <p
            data-testid="headline-value"
            className="relative mt-2 break-all font-mono text-2xl font-semibold tracking-tight tabular-nums text-[color:var(--color-text)] sm:text-3xl"
          >
            {formatResultValue(primary[1], precision)}
          </p>
        </section>
      ) : (
        <section className={`flex flex-wrap items-center justify-between gap-2 p-4 ${ui.card}`}>
          <p className="text-sm text-[color:var(--color-text-muted)]">No final value was produced.</p>
          <SolveStatusBadge status={status} />
        </section>
      )}

      {/* Stat row */}
      {stats.length > 0 && (
        <div
          data-testid="stat-row"
          className="flex flex-wrap items-center gap-3 rounded-[var(--radius-2)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-4 py-2.5"
        >
          {stats.map((stat, i) => (
            <span key={stat.label} className="flex items-center gap-2 text-xs">
              {i > 0 && (
                <span aria-hidden="true" className="h-3 w-px bg-[color:var(--color-border)]" />
              )}
              <span className="font-medium text-[color:var(--color-text-muted)]">{stat.label}</span>
              <span className="font-mono font-semibold tabular-nums text-[color:var(--color-text)]">
                {stat.value}
              </span>
            </span>
          ))}
        </div>
      )}

      {/* Plain-language summary */}
      {summaryText && (
        <p data-testid="result-summary" className="text-sm leading-relaxed text-[color:var(--color-text-muted)]">
          {summaryText}
        </p>
      )}

      {/* Additional results */}
      {rest.length > 0 && (
        <section className={`p-4 ${ui.card}`}>
          <h3 className="text-sm font-semibold text-[color:var(--color-text)]">All results</h3>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {rest.map(([key, value]) => (
              <div
                key={key}
                className="rounded-[var(--radius-1)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-2.5"
              >
                <dt className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
                  {humanize(key)}
                </dt>
                <dd className="mt-0.5 break-all font-mono text-sm font-medium tabular-nums text-[color:var(--color-text)]">
                  {formatResultValue(value, precision)}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* Error & convergence metrics */}
      {(errors.absolute !== null || errors.order_of_convergence !== null) && (
        <section className={`p-4 ${ui.card}`}>
          <div className="flex items-center gap-2">
            <span className={`${ui.iconBox} h-7 w-7`}>
              <Icon name="chart" size={14} />
            </span>
            <h3 className="text-sm font-semibold text-[color:var(--color-text)]">
              Error &amp; convergence
            </h3>
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-3">
            {[
              { label: "Absolute error", value: errors.absolute },
              {
                label: "Relative error",
                value:
                  errors.relative_percent === null || errors.relative_percent === undefined
                    ? null
                    : `${errors.relative_percent} %`,
              },
              { label: "Order of convergence", value: errors.order_of_convergence },
            ]
              .filter((m) => m.value !== null && m.value !== undefined)
              .map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-[var(--radius-1)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-2.5"
                >
                  <dt className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
                    {metric.label}
                  </dt>
                  <dd className="mt-0.5 font-mono text-sm tabular-nums text-[color:var(--color-text)]">
                    {typeof metric.value === "number"
                      ? formatResultValue(metric.value, precision)
                      : metric.value}
                  </dd>
                </div>
              ))}
          </dl>
        </section>
      )}

      {/* Result footer with next actions */}
      <footer
        data-testid="result-footer"
        className="flex flex-wrap items-center gap-2 rounded-[var(--radius-2)] border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-4 py-3"
      >
        <span className="mr-auto text-xs text-[color:var(--color-text-muted)]">
          What&apos;s next?
        </span>
        <button type="button" className={ui.btnGhost}>
          <Icon name="refresh" size={13} /> Re-solve
        </button>
        <button type="button" className={ui.btnGhost}>
          <Icon name="copy" size={13} /> Copy result
        </button>
        <button type="button" className={ui.btnGhost}>
          <Icon name="download" size={13} /> Export
        </button>
      </footer>
    </div>
  );
}

/** Build a one-line plain-language summary of the solve result. */
function buildSummary(
  response: SolveResponse,
  precision: number,
  methodName?: string,
): string {
  const entries = Object.entries(response.result);
  const [primary] = entries;
  if (!primary) return "";

  const name = methodName ?? response.method.replace(/_/g, " ");
  const value = formatResultValue(primary[1], precision);

  switch (response.status) {
    case "converged":
      return `The ${name} method converged to ${humanize(primary[0])} = ${value} in ${response.steps.length} step${response.steps.length === 1 ? "" : "s"}.`;
    case "diverged":
      return `The ${name} method diverged. The last computed value was ${value}. Consider trying a different initial guess.`;
    case "max_iter":
      return `The ${name} method reached the maximum iteration limit. The best approximation is ${value}.`;
    case "failed":
      return `The ${name} method failed to produce a result. ${response.warnings.length > 0 ? response.warnings[0] : "Check your inputs."}`;
    default:
      return `Result: ${humanize(primary[0])} = ${value}.`;
  }
}
