import { useEffect, useRef, useState } from "react";

import { ui } from "../utils/ui";
import { Icon } from "./ui/Icon";

const SPEEDS = [0.5, 1, 1.5, 2] as const;
const STEP_DURATION = 1200;

const CIRCLE_GHOST =
  "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink-muted transition duration-150 hover:bg-surface-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 disabled:cursor-not-allowed disabled:opacity-30";
const CIRCLE_PRIMARY =
  "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-accent-solid text-white shadow-accent transition duration-150 hover:bg-accent-solid-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-40";

interface IterationPlayerProps {
  steps: { title: string }[];
  activeIndex: number;
  onChange: (index: number) => void;
  className?: string;
}

/** Playback controls for the exam-style working timeline. */
export function IterationPlayer({
  steps,
  activeIndex,
  onChange,
  className = "",
}: IterationPlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  const last = Math.max(0, steps.length - 1);
  const index = Math.min(Math.max(activeIndex, 0), last);
  const current = steps[index];

  useEffect(() => {
    if (!playing || steps.length <= 1 || index >= last) return;
    const timer = window.setTimeout(() => {
      const next = index + 1;
      onChangeRef.current(next);
      if (next >= last) setPlaying(false);
    }, STEP_DURATION / speed);
    return () => window.clearTimeout(timer);
  }, [playing, index, last, speed, steps.length]);

  if (steps.length === 0) return null;

  function togglePlay(): void {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (index >= last) onChange(0);
    setPlaying(true);
  }

  function move(next: number): void {
    setPlaying(false);
    onChange(Math.min(Math.max(next, 0), last));
  }

  function changeSpeed(): void {
    const currentIndex = SPEEDS.indexOf(speed);
    setSpeed(SPEEDS[(currentIndex + 1) % SPEEDS.length]);
  }

  return (
    <section
      aria-label="Iteration player"
      className={`overflow-hidden rounded-panel border border-line bg-surface shadow-card ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-surface-muted/60 px-3 py-2.5">
        <span className={`${ui.iconBox} h-8 w-8`}>
          <Icon name={playing ? "pause" : "play"} size={14} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
              Iteration player
            </p>
            <span className="rounded-pill bg-surface px-1.5 py-0.5 text-2xs font-semibold tabular-nums text-ink-muted ring-1 ring-inset ring-line">
              {index + 1} / {steps.length}
            </span>
          </div>
          <p className="truncate text-sm font-semibold text-ink">{current.title}</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => move(index - 1)}
            disabled={index === 0}
            aria-label="Previous step"
            title="Previous step"
            className={CIRCLE_GHOST}
          >
            <Icon name="chevronLeft" size={15} />
          </button>
          <button
            type="button"
            onClick={togglePlay}
            disabled={steps.length <= 1}
            aria-label={playing ? "Pause playback" : "Play iterations"}
            title={playing ? "Pause" : "Play iterations"}
            className={CIRCLE_PRIMARY}
          >
            <Icon name={playing ? "pause" : "play"} size={14} />
          </button>
          <button
            type="button"
            onClick={() => move(index + 1)}
            disabled={index === last}
            aria-label="Next step"
            title="Next step"
            className={CIRCLE_GHOST}
          >
            <Icon name="chevronRight" size={15} />
          </button>
          <button
            type="button"
            onClick={changeSpeed}
            aria-label={`Playback speed ${speed}×. Change speed`}
            title="Change playback speed"
            className={`${ui.btnGhost} h-8 min-w-[2.5rem] justify-center px-1.5 text-2xs font-semibold tabular-nums`}
          >
            {speed}×
          </button>
        </div>
      </div>
      <div className="flex items-center gap-3 px-3 py-2.5">
        <input
          type="range"
          min={1}
          max={steps.length}
          step={1}
          value={index + 1}
          onChange={(event) => move(Number(event.target.value) - 1)}
          aria-label="Iteration step"
          aria-valuetext={`Step ${index + 1} of ${steps.length}: ${current.title}`}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-pill bg-line accent-accent-solid focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
        />
        <span className="shrink-0 text-2xs font-medium tabular-nums text-ink-muted">
          {playing ? "Playing" : "Ready"}
        </span>
      </div>
    </section>
  );
}
