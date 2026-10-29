import { useSidebarStore } from "../../store/sidebar";

/** Floating handle at the left edge when the sidebar is hidden. */
export function SidebarOpenHandle() {
  const setMode = useSidebarStore((state) => state.setMode);

  return (
    <button
      type="button"
      aria-label="Open navigation sidebar"
      aria-keyshortcuts="Ctrl+B Meta+B"
      title="Open navigation (Ctrl+B / ⌘B)"
      onClick={() => setMode("expanded")}
      className="fixed left-0 top-1/2 z-40 h-16 w-8 shrink-0 items-center justify-center rounded-r-xl border-r border-line-strong bg-surface shadow-sm text-ink transition hover:bg-surface-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 dark:border-white/[0.12] dark:bg-[#0f172a] dark:text-slate-300"
    >
      <span className="sr-only">Open sidebar (Ctrl+B / ⌘B)</span>
      <span className="text-[10px] font-semibold text-ink-muted writing-mode-vertical-rl rotate-180 dark:text-slate-400">
        Menu
      </span>
    </button>
  );
}
