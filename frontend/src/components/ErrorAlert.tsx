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
      className={`rounded-panel border border-danger/20 bg-danger-soft p-4 text-sm ${className}`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-danger/10 text-danger ring-1 ring-inset ring-danger/20">
          <Icon name="alert" size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-2xs font-semibold uppercase tracking-wide text-danger">
            Something went wrong
          </p>
          <p className="mt-1 font-medium text-ink">{error.message}</p>
          {error.hint && (
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">{error.hint}</p>
          )}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="rounded-control p-1.5 text-danger/70 transition duration-150 hover:bg-danger/10 hover:text-danger focus:outline-none focus-visible:ring-2 focus-visible:ring-danger"
          >
            <Icon name="close" size={15} />
          </button>
        )}
      </div>
    </div>
  );
}
