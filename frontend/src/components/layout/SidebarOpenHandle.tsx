import { useRef } from "react";

import { useSidebarStore } from "../../store/sidebar";

/** Floating handle at the left edge when the sidebar is hidden. */
export function SidebarOpenHandle() {
  const setMode = useSidebarStore((state) => state.setMode);
  const setWidth = useSidebarStore((state) => state.setWidth);
  const startX = useRef(0);
  const dragging = useRef(false);

  return (
    <button
      type="button"
      aria-label="Open sidebar"
      aria-keyshortcuts="Ctrl+B Meta+B"
      title="Open sidebar (Ctrl+B / ⌘B)"
      onClick={() => setMode("rail")}
      onPointerDown={(event) => {
        event.preventDefault();
        startX.current = event.clientX;
        dragging.current = false;
      }}
      onPointerMove={(event) => {
        if (dragging.current) return;
        if (event.clientX - startX.current > 20) {
          dragging.current = true;
          setMode("rail");
          setWidth(56);
        }
      }}
      onPointerUp={() => {
        dragging.current = false;
      }}
      className="sidebar-open-handle fixed left-0 top-1/2 z-50 -translate-y-1/2 flex h-24 w-8 items-center justify-center gap-1 rounded-r-[12px] bg-white shadow-md transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 dark:bg-[#0f172a] dark:hover:bg-[#111a2c]"
      style={{ touchAction: "none" }}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="text-slate-600 dark:text-slate-300">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M9 4v16" />
      </svg>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-600 [writing-mode:vertical-rl] rotate-180 dark:text-slate-300">
        MENU
      </span>
    </button>
  );
}
