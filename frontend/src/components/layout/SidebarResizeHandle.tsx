import { useCallback, useEffect, useRef, useState } from "react";

import { useSidebarStore } from "../../store/sidebar";

/**
 * Drag handle on the right edge of the expanded sidebar.
 * Drag to resize (240–420 px), double-click to reset to 280 px.
 * Keyboard accessible: Enter/Space activates, Arrow keys adjust width.
 */
export function SidebarResizeHandle() {
  const width = useSidebarStore((state) => state.width);
  const setWidth = useSidebarStore((state) => state.setWidth);
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const startWidth = useRef(width);

  const startDrag = useCallback(
    (clientX: number) => {
      setIsDragging(true);
      startX.current = clientX;
      startWidth.current = width;
    },
    [width]
  );

  const move = useCallback(
    (clientX: number) => {
      if (!isDragging) return;
      const delta = clientX - startX.current;
      setWidth(startWidth.current + delta);
    },
    [isDragging, setWidth, startWidth]
  );

  const stop = useCallback(() => {
    setIsDragging(false);
  }, []);

  const reset = useCallback(() => {
    setWidth(280);
  }, [setWidth]);

  useEffect(() => {
    if (!isDragging) return;
    window.addEventListener("mousemove", (e) => move(e.clientX));
    window.addEventListener("mouseup", stop);
    return () => {
      window.removeEventListener("mousemove", (e) => move(e.clientX));
      window.removeEventListener("mouseup", stop);
    };
  }, [isDragging, move, stop]);

  return (
    <div
      role="separator"
      aria-label="Resize sidebar width"
      aria-valuenow={width}
      aria-valuemin={240}
      aria-valuemax={420}
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          reset();
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          setWidth(width + 10);
        } else if (event.key === "ArrowLeft") {
          event.preventDefault();
          setWidth(width - 10);
        }
      }}
      onDoubleClick={reset}
      onMouseDown={(event) => {
        event.preventDefault();
        startDrag(event.clientX);
      }}
      onTouchStart={(event) => {
        event.preventDefault();
        startDrag(event.touches[0].clientX);
      }}
      className="absolute top-0 bottom-0 right-0 w-2 cursor-ew-resize select-none hover:bg-indigo-200/40 dark:hover:bg-indigo-500/10 transition-colors"
    />
  );
}
