import type { ApiError } from "../../api/client";
import { ui } from "../../utils/ui";
import { Icon } from "./Icon";

interface ErrorStateProps {
  title?: string;
  error?: ApiError;
  message?: string;
  hint?: string;
  onRetry?: () => void;
  retryLabel?: string;
  compact?: boolean;
  className?: string;
}

/** Friendly page/section error with an explicit recovery action. */
export function ErrorState({
  title = "Something went wrong",
  error,
  message,
  hint,
  onRetry,
  retryLabel = "Try again",
  compact = false,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`rounded-panel border border-danger/20 bg-danger-soft text-left ${compact ? "p-3.5" : "p-6"} ${className}`}
    >
      <div className={`flex items-start ${compact ? "gap-2.5" : "gap-3"}`}>
        <span
          className={`${compact ? "h-8 w-8" : "h-10 w-10"} flex shrink-0 items-center justify-center rounded-control bg-danger/10 text-danger ring-1 ring-inset ring-danger/20`}
        >
          <Icon name="alert" size={compact ? 16 : 20} />
        </span>
        <div className="min-w-0 flex-1">
          <p
            className={`${compact ? "text-sm" : "text-base"} font-semibold text-ink`}
          >
            {title}
          </p>
          <p className={`${compact ? "mt-0.5 text-xs" : "mt-1 text-sm"} leading-relaxed text-ink-muted`}>
            {message ?? error?.message ?? "The request could not be completed."}
          </p>
          {(hint ?? error?.hint) && (
            <p className="mt-1.5 text-2xs leading-relaxed text-ink-muted">
              {hint ?? error?.hint}
            </p>
          )}
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className={`${ui.btn} mt-3 px-3 py-1.5 text-xs`}
            >
              <Icon name="refresh" size={13} />
              {retryLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
