import { useCallback, useEffect, useRef, useState } from "react";

import { useSidebarStore } from "../../store/sidebar";

function widthToState(w: number): "hidden" | "rail" | "expanded" {
  if (w < 40) return "hidden";
  if (w <= 140) return "rail";
  return "expanded";
}

/**
 * Drag handle on the right edge of the sidebar.
 * Works in rail/expanded/hidden with snap behavior and live preview.
 */
export function SidebarResizeHandle() {
  const width = useSidebarStore((state) => state.width);
  const mode = useSidebarStore((state) => state.mode);
  const setWidth = useSidebarStore((state) => state.setWidth);
  const setMode = useSidebarStore((state) => state.setMode);
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const startWidth = useRef(width);
  const [previewWidth, setPreviewWidth] = useState(width);

  const reset = useCallback(() => {
    setMode("expanded");
    setWidth(280);
  }, [setMode, setWidth]);

  const startDrag = useCallback(
    (clientX: number) => {
      setIsDragging(true);
      startX.current = clientX;
      startWidth.current = width;
      setPreviewWidth(width);
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";
      document.body.style.pointerEvents = "none";
    },
    [width]
  );

  const move = useCallback(
    (clientX: number) => {
      if (!isDragging) return;
      const delta = clientX - startX.current;
      const raw = startWidth.current + delta;
      let w = raw;
      if (w < 40) w = 0;
      else if (w <= 140) w = 56;
      else if (w < 240) w = 240;
      else if (w > 420) w = 420;
      else w = Math.round(w);
      setPreviewWidth(w);
    },
    [isDragging]
  );

  const stop = useCallback(() => {
    if (!isDragging) return;
    const state = widthToState(previewWidth);
    if (state === "hidden") {
      setMode("hidden");
      setWidth(0);
    } else if (state === "rail") {
      setMode("rail");
      setWidth(56);
    } else {
      setMode("expanded");
      const w = previewWidth < 240 ? 280 : Math.min(420, Math.max(240, previewWidth));
      setWidth(w);
    }
    setIsDragging(false);
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
    document.body.style.pointerEvents = "";
  }, [isDragging, previewWidth, setMode, setWidth]);

  useEffect(() => {
    if (!isDragging) return;
    const handleMove = (e: PointerEvent) => {
      e.preventDefault();
      move(e.clientX);
    };
    const handleUp = (e: PointerEvent) => {
      e.preventDefault();
      stop();
    };
    window.addEventListener("pointermove", handleMove, { passive: false });
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
    };
  }, [isDragging, move, stop]);

  // preview width shown via overlay label

  return (
    <>
      <div
        role="separator"
        aria-label="Resize sidebar"
        aria-orientation="vertical"
        aria-valuenow={mode === "expanded" ? width : mode === "rail" ? 56 : 0}
        aria-valuemin={0}
        aria-valuemax={420}
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            reset();
            return;
          }
          if (event.key === "Home") {
            event.preventDefault();
            setMode("rail");
            setWidth(56);
            return;
          }
          if (event.key === "End") {
            event.preventDefault();
            setMode("expanded");
            setWidth(420);
            return;
          }
          if (event.key === "ArrowRight") {
            event.preventDefault();
            const step = event.shiftKey ? 48 : 16;
            if (mode === "rail") {
              setMode("expanded");
              setWidth(Math.min(420, Math.max(240, 280 + step)));
            } else if (mode === "expanded") {
              setWidth(Math.min(420, width + step));
            } else if (mode === "hidden") {
              setMode("rail");
              setWidth(56);
            }
            return;
          }
          if (event.key === "ArrowLeft") {
            event.preventDefault();
            const step = event.shiftKey ? 48 : 16;
            if (mode === "expanded") {
              const nw = width - step;
              if (nw < 140) {
                setMode("rail");
                setWidth(56);
              } else {
                setWidth(Math.max(240, nw));
              }
            } else if (mode === "rail") {
              setMode("hidden");
              setWidth(0);
            }
            return;
          }
        }}
        onDoubleClick={reset}
        onPointerDown={(event) => {
          event.preventDefault();
          startDrag(event.clientX);
        }}
        className={`absolute top-0 bottom-0 right-[-5px] w-[10px] cursor-col-resize group focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500`}
        style={{ touchAction: "none" }}
      >
        <div
          className={`absolute left-1/2 top-0 h-full -translate-x-1/2 transition-colors ${
            isDragging ? "w-[2px] bg-indigo-500" : "w-[2px] bg-transparent group-hover:bg-indigo-400/70"
          }`}
        />
        <div
          className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-slate-200 bg-white px-1 py-1 shadow-sm transition-opacity dark:border-white/[0.12] dark:bg-[#0f172a] ${
            isDragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"
          }`}
        >
          <svg width="10" height="12" viewBox="0 0 10 12" className="text-slate-400">
            <circle cx="3" cy="3" r="1" />
            <circle cx="7" cy="3" r="1" />
            <circle cx="3" cy="6" r="1" />
            <circle cx="7" cy="6" r="1" />
            <circle cx="3" cy="9" r="1" />
            <circle cx="7" cy="9" r="1" />
          </svg>
        </div>
      </div>
      {isDragging && (
        <div
          className="fixed left-1/2 top-4 -translate-x-1/2 z-[100] rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white shadow-lg dark:bg-white dark:text-slate-900"
          role="status"
        >
          {previewWidth === 0 ? "Hidden" : previewWidth <= 56 ? "Rail (56 px)" : `Expanded · ${previewWidth}px`}
        </div>
      )}
    </>
  );
}
