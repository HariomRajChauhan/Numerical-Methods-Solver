import type { PointerEventHandler } from "react";

interface ResizeDividerProps {
  value: number;
  min: number;
  max: number;
  resizing: boolean;
  onPointerDown: PointerEventHandler<HTMLDivElement>;
  onPointerMove: PointerEventHandler<HTMLDivElement>;
  onPointerUp: PointerEventHandler<HTMLDivElement>;
  onPointerCancel: PointerEventHandler<HTMLDivElement>;
  onNudge: (delta: number) => void;
  onReset: () => void;
}

/** Accessible vertical split handle between the input and result panes. */
export function ResizeDivider({
  value,
  min,
  max,
  resizing,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPointerCancel,
  onNudge,
  onReset,
}: ResizeDividerProps) {
  return (
    <div
      role="separator"
      aria-label="Resize the input and result panels"
      aria-orientation="vertical"
      aria-valuenow={Math.round(value)}
      aria-valuemin={min}
      aria-valuemax={max}
      tabIndex={0}
      title="Drag to resize · double-click to reset"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
      onDoubleClick={onReset}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          onNudge(-2);
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          onNudge(2);
        } else if (event.key === "Home") {
          event.preventDefault();
          onReset();
        }
      }}
      className={`group relative hidden w-3 shrink-0 cursor-col-resize touch-none select-none items-center justify-center rounded-pill focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 lg:flex ${
        resizing ? "bg-accent-soft" : ""
      }`}
    >
      <span aria-hidden="true" className="h-full w-px bg-line" />
      <span
        aria-hidden="true"
        className={`absolute top-1/2 flex h-10 w-2 -translate-y-1/2 items-center justify-center rounded-pill border border-line bg-surface shadow-sm transition duration-150 group-hover:border-accent-300 group-hover:bg-accent-soft group-focus-visible:border-accent-300 ${
          resizing ? "border-accent-300 bg-accent-soft" : ""
        }`}
      >
        <span className="h-4 w-px rounded-pill bg-line-strong" />
        <span className="ml-0.5 h-4 w-px rounded-pill bg-line-strong" />
      </span>
    </div>
  );
}
