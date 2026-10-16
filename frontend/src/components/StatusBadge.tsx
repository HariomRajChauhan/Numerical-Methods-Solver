import type { MethodStatus, SolveStatus } from "../types/api";

const SOLVE_STYLES: Record<SolveStatus, { label: string; className: string }> = {
  converged: {
    label: "Converged",
    className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300",
  },
  diverged: {
    label: "Diverged",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300",
  },
  max_iter: {
    label: "Max iterations",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300",
  },
  failed: {
    label: "Failed",
    className: "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300",
  },
};

const METHOD_STYLES: Record<MethodStatus, { label: string; className: string }> = {
  available: {
    label: "Available",
    className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300",
  },
  coming_soon: {
    label: "Coming soon",
    className: "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  },
};

export function SolveStatusBadge({ status }: { status: SolveStatus }) {
  const { label, className } = SOLVE_STYLES[status];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}>
      {label}
    </span>
  );
}

export function MethodStatusBadge({ status }: { status: MethodStatus }) {
  const { label, className } = METHOD_STYLES[status];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
