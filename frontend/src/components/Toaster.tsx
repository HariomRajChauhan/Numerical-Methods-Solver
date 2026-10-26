import { useEffect, useState } from "react";

import { type ToastMessage, useToastStore } from "../store/toast";
import { Icon, type IconName } from "./ui/Icon";

const TONE: Record<
  ToastMessage["tone"],
  { icon: IconName; label: string; accent: string; iconClass: string }
> = {
  success: {
    icon: "check",
    label: "Success",
    accent: "border-success/25",
    iconClass: "bg-success-soft text-success ring-success/20",
  },
  error: {
    icon: "alert",
    label: "Error",
    accent: "border-danger/25",
    iconClass: "bg-danger-soft text-danger ring-danger/20",
  },
  info: {
    icon: "info",
    label: "Information",
    accent: "border-info/25",
    iconClass: "bg-info-soft text-info ring-info/20",
  },
};

/** Global, polite toast region mounted once by the app shell. */
export function Toaster() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);

  return (
    <div
      role="region"
      className="pointer-events-none fixed inset-x-4 bottom-4 z-[80] flex flex-col items-end gap-2 sm:left-auto sm:right-5 sm:bottom-5 sm:w-[23rem]"
      aria-label="Notifications"
    >
      {toasts.map((item) => (
        <ToastItem key={item.id} toast={item} onDismiss={dismiss} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: (id: number) => void;
}) {
  const [leaving, setLeaving] = useState(false);
  const [paused, setPaused] = useState(false);
  const tone = TONE[toast.tone];

  useEffect(() => {
    if (paused || leaving) return;
    const timer = window.setTimeout(() => setLeaving(true), toast.duration);
    return () => window.clearTimeout(timer);
  }, [paused, leaving, toast.duration]);

  useEffect(() => {
    if (!leaving) return;
    const timer = window.setTimeout(() => onDismiss(toast.id), 180);
    return () => window.clearTimeout(timer);
  }, [leaving, onDismiss, toast.id]);

  return (
    <div
      role={toast.tone === "error" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className={`animate-toast-in pointer-events-auto w-full rounded-panel border bg-surface/95 p-3.5 shadow-popover backdrop-blur-xl ${tone.accent} ${
        leaving ? "animate-toast-out" : ""
      }`}
    >
      <div className="flex items-start gap-2.5">
        <span
          role="img"
          aria-label={tone.label}
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-control ring-1 ring-inset ${tone.iconClass}`}
        >
          <Icon name={tone.icon} size={14} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink">{toast.title}</p>
          {toast.message && (
            <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">{toast.message}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setLeaving(true)}
          aria-label="Dismiss notification"
          className="rounded-control p-1 text-ink-subtle transition duration-150 hover:bg-surface-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
        >
          <Icon name="close" size={13} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
