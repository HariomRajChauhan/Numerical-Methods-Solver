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
      onClick={() => setMode("expanded")}
      onPointerDown={(event) => {
        event.preventDefault();
        startX.current = event.clientX;
        dragging.current = false;
      }}
      onPointerMove={(event) => {
        if (dragging.current) return;
        if (event.clientX - startX.current > 20) {
          dragging.current = true;
          setMode("expanded");
          setWidth(280);
        }
      }}
      onPointerUp={() => {
        dragging.current = false;
      }}
      className="sidebar-open-handle fixed left-0 top-1/2 z-50 -translate-y-1/2 flex h-12 w-2 items-center justify-center rounded-r-md bg-accent opacity-60 shadow-sm transition hover:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      style={{ touchAction: "none" }}
    />
  );
}
