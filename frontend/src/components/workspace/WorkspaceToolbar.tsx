import { useEffect, useRef, useState } from "react";

import { toast } from "../../store/toast";
import type { MethodExample } from "../../types/api";
import { copyText } from "../../utils/download";
import { ui } from "../../utils/ui";
import { ExportButtons } from "../ExportButtons";
import { Icon } from "../ui/Icon";

interface WorkspaceToolbarProps {
  formId: string;
  busy: boolean;
  canSolve: boolean;
  methodId: string;
  methodName: string;
  shareUrl: string;
  inputs: Record<string, unknown>;
  examples: MethodExample[];
  hasResult: boolean;
  inputsCollapsed: boolean;
  onToggleInputs: () => void;
  onLoadExample: (inputs: MethodExample["inputs"]) => void;
}

/** Sticky action bar shared by both workspace panes. */
export function WorkspaceToolbar({
  formId,
  busy,
  canSolve,
  methodId,
  methodName,
  shareUrl,
  inputs,
  examples,
  hasResult,
  inputsCollapsed,
  onToggleInputs,
  onLoadExample,
}: WorkspaceToolbarProps) {
  return (
    <div
      role="toolbar"
      aria-label="Solver actions"
      className="no-print sticky top-16 z-30 mb-5 flex flex-wrap items-center gap-2 rounded-panel border border-line bg-surface/90 p-2 shadow-card backdrop-blur-xl"
    >
      <button
        type="button"
        onClick={onToggleInputs}
        aria-expanded={!inputsCollapsed}
        aria-controls="workspace-inputs"
        className={`${ui.btn} px-2.5 py-2`}
        title={inputsCollapsed ? "Show inputs" : "Hide inputs"}
      >
        <Icon name="panelLeft" size={15} />
        <span className="hidden sm:inline">{inputsCollapsed ? "Show inputs" : "Hide inputs"}</span>
      </button>

      <button
        type="submit"
        form={formId}
        disabled={busy || !canSolve}
        aria-busy={busy}
        aria-keyshortcuts="Control+Enter Meta+Enter"
        title={canSolve ? "Solve (Ctrl/⌘ + Enter)" : "This method is coming soon"}
        className={`${ui.btnPrimary} px-4 py-2`}
      >
        <Icon
          name={busy ? "loader" : "play"}
          size={15}
          className={busy ? "animate-spin" : undefined}
        />
        {busy ? "Solving…" : "Solve"}
      </button>

      <span aria-hidden="true" className="mx-0.5 hidden h-5 w-px bg-line sm:block" />

      <div className="ml-auto flex flex-wrap items-center gap-1.5">
        <ExampleMenu
          examples={examples}
          onLoadExample={onLoadExample}
          disabled={!canSolve}
        />
        {hasResult && (
          <>
            <span aria-hidden="true" className="mx-0.5 hidden h-5 w-px bg-line sm:block" />
            <button
              type="button"
              onClick={() => window.print()}
              title="Print or save as PDF"
              aria-label="Print solution"
              className={`${ui.btn} px-2.5 py-2`}
            >
              <Icon name="printer" size={14} />
              <span className="hidden lg:inline">Print</span>
            </button>
            <ExportButtons methodId={methodId} inputs={inputs} compact />
          </>
        )}
        <ShareButton title={`${methodName} · Numerical Methods Solver`} url={shareUrl} />
      </div>
    </div>
  );
}

interface ExampleMenuProps {
  examples: MethodExample[];
  onLoadExample: (inputs: MethodExample["inputs"]) => void;
  disabled?: boolean;
}

function ExampleMenu({ examples, onLoadExample, disabled = false }: ExampleMenuProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function handlePointer(event: PointerEvent): void {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKey(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", handlePointer);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("pointerdown", handlePointer);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  if (examples.length === 0 || disabled) {
    return (
      <button
        type="button"
        disabled
        title={disabled ? "Examples unlock when this method is available" : "No examples yet"}
        className={`${ui.btn} px-2.5 py-2`}
      >
        <Icon name="sparkles" size={14} />
        Examples
      </button>
    );
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${ui.btn} px-2.5 py-2`}
      >
        <Icon name="sparkles" size={14} />
        Examples
        <Icon
          name="chevronDown"
          size={13}
          className={`transition duration-150 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div
          role="menu"
          aria-label="Worked examples"
          className="absolute right-0 top-full z-50 mt-2 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-panel border border-line bg-surface p-1.5 shadow-popover"
        >
          {examples.map((example) => (
            <button
              key={example.name}
              type="button"
              role="menuitem"
              onClick={() => {
                onLoadExample(example.inputs);
                setOpen(false);
                toast({
                  tone: "info",
                  title: "Example loaded",
                  message: example.name,
                  duration: 3200,
                });
              }}
              className="block w-full rounded-control px-2.5 py-2 text-left text-xs text-ink-muted transition duration-150 hover:bg-surface-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-500"
            >
              <span className="flex items-center gap-2">
                <Icon name="sparkles" size={12} className="shrink-0 text-accent-text" />
                <span className="font-medium">{example.name}</span>
              </span>
              {example.description && (
                <span className="mt-0.5 block pl-5 text-2xs text-ink-subtle">
                  {example.description}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface ShareButtonProps {
  title: string;
  url?: string;
}

function ShareButton({ title, url }: ShareButtonProps) {
  const [state, setState] = useState<"idle" | "copied" | "shared" | "error">("idle");
  const timerRef = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timerRef.current), []);

  function show(next: typeof state): void {
    setState(next);
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => setState("idle"), 2200);
  }

  function rememberState(link: string): void {
    if (!url) return;
    try {
      window.history.replaceState(window.history.state, "", link);
    } catch {
      // History can be unavailable in embedded previews; sharing still works.
    }
  }

  async function handleShare(): Promise<void> {
    const shareUrl = url ?? window.location.href;
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title, url: shareUrl });
        rememberState(shareUrl);
        show("shared");
        toast({
          tone: "success",
          title: "Link shared",
          message: "The current inputs and view are encoded in the link.",
        });
        return;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }
    const copied = await copyText(shareUrl);
    if (copied) {
      rememberState(shareUrl);
      show("copied");
      toast({
        tone: "success",
        title: "Share link copied",
        message: "The current inputs and view are encoded in the link.",
      });
    } else {
      show("error");
      toast({
        tone: "error",
        title: "Could not copy the link",
        message: "Your browser blocked clipboard access. Copy the address bar instead.",
      });
    }
  }

  const label =
    state === "copied"
      ? "Link copied"
      : state === "shared"
        ? "Shared"
        : state === "error"
          ? "Copy failed"
          : "Share";

  return (
    <button
      type="button"
      onClick={() => void handleShare()}
      className={`${ui.btn} px-2.5 py-2`}
      aria-live="polite"
      title="Share this solver"
    >
      <Icon name={state === "copied" || state === "shared" ? "check" : "share"} size={14} />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
