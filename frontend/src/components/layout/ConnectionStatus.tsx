import { retryBackendConnection, useBackendConnectionStore } from "../../store/connection";
import { Icon } from "../ui/Icon";

const COPY = {
  checking: {
    label: "Connecting…",
    description: "Connecting to solver…",
    className: "border-line bg-surface-muted text-ink-muted",
  },
  waking: {
    label: "Waking solver…",
    description:
      "Waking up the solver. This may take a moment on the free hosting plan.",
    className: "border-warning/20 bg-warning-soft text-warning",
  },
  ready: {
    label: "Connected",
    description: "Solver connected.",
    className: "border-success/20 bg-success-soft text-success",
  },
  error: {
    label: "Offline",
    description: "Unable to connect to the solver. Please try again.",
    className: "border-danger/20 bg-danger-soft text-danger",
  },
} as const;

/** Compact, non-blocking backend readiness indicator for the global header. */
export function ConnectionStatus() {
  const status = useBackendConnectionStore((state) => state.status);
  const copy = COPY[status];
  const busy = status === "checking" || status === "waking";

  return (
    <div
      title={copy.description}
      className={`flex h-8 items-center gap-1.5 rounded-pill border px-2 transition-colors duration-150 ${copy.className}`}
    >
      <span
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="flex items-center gap-1.5"
      >
        {busy ? (
          <Icon name="loader" size={12} className="shrink-0 animate-spin" aria-hidden="true" />
        ) : status === "ready" ? (
          <Icon name="check" size={12} className="shrink-0" aria-hidden="true" />
        ) : (
          <Icon name="alert" size={12} className="shrink-0" aria-hidden="true" />
        )}
        <span
          aria-hidden="true"
          className={`text-2xs font-medium ${
            status === "ready" ? "hidden lg:inline" : "hidden sm:inline"
          }`}
        >
          {copy.label}
        </span>
        <span className="sr-only">{copy.description}</span>
      </span>
      {status === "error" && (
        <button
          type="button"
          onClick={() => void retryBackendConnection()}
          className="ml-0.5 rounded-pill px-1.5 py-0.5 text-2xs font-semibold underline-offset-2 transition hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]"
        >
          Retry
        </button>
      )}
    </div>
  );
}
