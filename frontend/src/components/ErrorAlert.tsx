import { ApiError } from "../api/client";

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
      className={`rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm dark:border-rose-900/60 dark:bg-rose-950/40 ${className}`}
    >
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-lg leading-none text-rose-500">
          ⚠
        </span>
        <div className="flex-1">
          <p className="font-medium text-rose-800 dark:text-rose-200">{error.message}</p>
          {error.hint && <p className="mt-1 text-rose-700/80 dark:text-rose-300/80">{error.hint}</p>}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="rounded p-1 text-rose-500 transition hover:bg-rose-100 dark:hover:bg-rose-900/40"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
