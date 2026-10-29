import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

import { Icon } from "../ui/Icon";

interface Shortcut {
  keys: string[];
  label: string;
}

interface ShortcutSection {
  title: string;
  items: Shortcut[];
}

const SECTIONS: ShortcutSection[] = [
  {
    title: "Search & navigation",
    items: [
      { keys: ["Ctrl", "K"], label: "Search methods" },
      { keys: ["⌘", "K"], label: "Search methods on macOS" },
      { keys: ["/"], label: "Focus the method search" },
      { keys: ["?"], label: "Open this shortcut sheet" },
      { keys: ["Esc"], label: "Close search, dialogs or the mobile menu" },
    ],
  },
  {
    title: "Solver",
    items: [
      { keys: ["Ctrl", "Enter"], label: "Solve from an input field" },
      { keys: ["⌘", "Enter"], label: "Solve on macOS" },
      { keys: ["Alt", "1–7"], label: "Switch between the solver tabs" },
      { keys: ["←", "→"], label: "Move between tabs when the tab bar is focused" },
    ],
  },
];

interface ShortcutsSheetProps {
  open: boolean;
  onClose: () => void;
}

/** Accessible keyboard-shortcut dialog opened with “?” or the header button. */
export function ShortcutsSheet({ open, onClose }: ShortcutsSheetProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus.current?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[90] flex items-end justify-center bg-slate-950/45 p-3 backdrop-blur-sm sm:items-center sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="animate-fade-up max-h-[min(44rem,calc(100dvh-1.5rem))] w-full max-w-lg overflow-y-auto rounded-3xl border border-line bg-surface p-5 shadow-popover scroll-slim sm:p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-pill border border-accent-soft-line bg-accent-soft px-2.5 py-1 text-2xs font-semibold uppercase tracking-wide text-accent-text">
              <Icon name="keyboard" size={13} />
              Keyboard
            </span>
            <h2 id={titleId} className="mt-3 text-xl font-bold tracking-tight text-ink">
              Work faster with shortcuts
            </h2>
            <p id={descriptionId} className="mt-1 text-xs leading-relaxed text-ink-muted">
              Shortcuts work when you are not typing in a text field. Press{" "}
              <kbd className="rounded border border-line bg-surface-muted px-1 font-mono text-[10px] text-ink-muted">
                ?
              </kbd>{" "}
              anywhere to reopen this sheet.
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close keyboard shortcuts"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink-subtle transition hover:bg-surface-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
          >
            <Icon name="close" size={16} />
          </button>
        </div>

        <div className="mt-6 space-y-6">
          {SECTIONS.map((section) => (
            <section key={section.title}>
              <h3 className="text-2xs font-semibold uppercase tracking-[0.16em] text-ink-muted">
                {section.title}
              </h3>
              <dl className="mt-2 divide-y divide-line overflow-hidden rounded-panel border border-line">
                {section.items.map((item) => (
                  <div
                    key={`${section.title}-${item.keys.join("-")}`}
                    className="flex items-center justify-between gap-4 bg-surface px-3.5 py-2.5"
                  >
                    <dt className="text-xs text-ink-muted">{item.label}</dt>
                    <dd className="flex shrink-0 items-center gap-1">
                      {item.keys.map((key) => (
                        <kbd
                          key={key}
                          className="min-w-6 rounded-md border border-line bg-surface-muted px-1.5 py-0.5 text-center font-mono text-[10px] font-semibold text-ink shadow-sm"
                        >
                          {key}
                        </kbd>
                      ))}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>

        <p className="mt-5 flex items-start gap-2 rounded-control border border-line bg-surface-muted p-3 text-2xs leading-relaxed text-ink-muted">
          <Icon name="info" size={14} className="mt-0.5 shrink-0 text-accent-text" />
          On macOS use ⌘ instead of Ctrl. The browser may reserve some system shortcuts.
        </p>
      </div>
    </div>,
    document.body,
  );
}
