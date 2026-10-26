import { ApiError } from "../api/client";
import { Icon } from "./ui/Icon";

interface ErrorAlertProps {
  error: ApiError;
  onDismiss?: () => void;
  className?: string;
}

/** Friendly, non-technical error box (never a stack trace). */
export function ErrorAlert({ error, onDismiss, className = "" }: ErrorAlertProps) {
  return (
    <div
      role="alert"
      className={`rounded-2xl border border-rose-200/80 bg-rose-50/90 p-4 text-sm dark:border-rose-500/20 dark:bg-rose-500/[0.07] ${className}`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300">
          <Icon name="alert" size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-500 dark:text-rose-400">
            Something went wrong
          </p>
          <p className="mt-1 font-medium text-rose-800 dark:text-rose-200">{error.message}</p>
          {error.hint && (
            <p className="mt-1 text-xs leading-relaxed text-rose-700/80 dark:text-rose-300/80">
              {error.hint}
            </p>
          )}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="rounded-lg p-1.5 text-rose-400 transition hover:bg-rose-100 hover:text-rose-600 dark:hover:bg-rose-500/15 dark:hover:text-rose-200"
          >
            <Icon name="close" size={15} />
          </button>
        )}
      </div>
    </div>
  );
}
