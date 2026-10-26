import type { MethodStatus, SolveStatus } from "../types/api";

const SOLVE_STYLES: Record<SolveStatus, { label: string; className: string; dot: string }> = {
  converged: {
    label: "Converged",
    className: "bg-success-soft text-success ring-success/20",
    dot: "bg-success",
  },
  diverged: {
    label: "Diverged",
    className: "bg-warning-soft text-warning ring-warning/20",
    dot: "bg-warning",
  },
  max_iter: {
    label: "Max iterations",
    className: "bg-warning-soft text-warning ring-warning/20",
    dot: "bg-warning",
  },
  failed: {
    label: "Failed",
    className: "bg-danger-soft text-danger ring-danger/20",
    dot: "bg-danger",
  },
};

const METHOD_STYLES: Record<MethodStatus, { label: string; className: string; dot: string }> = {
  available: {
    label: "Available",
    className: "bg-success-soft text-success ring-success/20",
    dot: "bg-success",
  },
  coming_soon: {
    label: "Coming soon",
    className: "bg-surface-muted text-ink-muted ring-line",
    dot: "bg-ink-subtle",
  },
};

export function SolveStatusBadge({ status }: { status: SolveStatus }) {
  const { label, className, dot } = SOLVE_STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-2xs font-semibold ring-1 ring-inset ${className}`}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export function MethodStatusBadge({ status }: { status: MethodStatus }) {
  const { label, className, dot } = METHOD_STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-2xs font-medium ring-1 ring-inset ${className}`}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}
