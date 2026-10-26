import { useEffect, useMemo, useRef, useState } from "react";

import { useReducedMotion } from "../hooks/useReducedMotion";
import type { Step } from "../types/api";
import { ui } from "../utils/ui";
import { CopyButton } from "./CopyButton";
import { IterationPlayer } from "./IterationPlayer";
import { LatexView } from "./LatexView";
import { Icon } from "./ui/Icon";

interface StepsPanelProps {
  steps: Step[];
}

/** Numeric values introduced by a step, ignoring LaTeX subscript indices. */
function changedValues(step: Step, previous?: Step): string[] {
  if (!previous) return [];
  const current = numericTokens(step);
  const before = new Set(numericTokens(previous).map(Number));
  const seen = new Set<number>();
  return current
    .filter((token) => {
      const value = Number(token);
      if (!Number.isFinite(value) || before.has(value) || seen.has(value)) return false;
      seen.add(value);
      return true;
    })
    .slice(0, 4);
}

function numericTokens(step: Step): string[] {
  const latex = step.latex.replace(/_\{[^}]*\}/g, "");
  const matches = latex.match(/-?\d+(?:\.\d+)?/g) ?? [];
  return matches.filter((token) => {
    if (token.includes(".") || token.startsWith("-")) return true;
    return Math.abs(Number(token)) > 100;
  });
}

/** Exam-style working: numbered timeline, anchor links, KaTeX, collapsible cards. */
export function StepsPanel({ steps }: StepsPanelProps) {
  const [activeIndex, setActiveIndex] = useState(() => Math.max(0, steps.length - 1));
  const stepRefs = useRef<(HTMLLIElement | null)[]>([]);
  const shouldScroll = useRef(false);
  const reducedMotion = useReducedMotion();
  const currentIndex = Math.min(activeIndex, Math.max(0, steps.length - 1));

  useEffect(() => {
    if (!shouldScroll.current) return;
    shouldScroll.current = false;
    stepRefs.current[currentIndex]?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "center",
    });
  }, [currentIndex, reducedMotion]);

  const asText = useMemo(
    () =>
      steps
        .map((step, index) => {
          const parts = [`${index + 1}. ${step.title}`];
          if (step.latex) parts.push(`   ${step.latex}`);
          if (step.note) parts.push(`   (${step.note})`);
          return parts.join("\n");
        })
        .join("\n\n"),
    [steps],
  );

  if (steps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-panel border border-dashed border-line-strong bg-surface-muted px-6 py-12 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-control bg-surface text-ink-subtle shadow-sm">
          <Icon name="list" size={19} />
        </span>
        <p className="text-sm text-ink-muted">No working steps were produced.</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <IterationPlayer
        steps={steps}
        activeIndex={currentIndex}
        onChange={(index) => {
          shouldScroll.current = true;
          setActiveIndex(index);
        }}
        className="mb-4"
      />

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={ui.sectionLabel}>Working</p>
          <p className="mt-0.5 text-xs text-ink-muted">
            <span className="tabular-nums">{steps.length}</span> step
            {steps.length === 1 ? "" : "s"} · rendered with KaTeX
          </p>
        </div>
        <CopyButton text={asText} label="Copy working" />
      </div>

      <div className="relative">
        <span
          aria-hidden="true"
          className="absolute bottom-4 left-[17px] top-4 w-px bg-gradient-to-b from-accent-soft-line via-line to-transparent"
        />
        <ol className="list-none space-y-3">
          {steps.map((step, index) => {
            const changed = changedValues(step, steps[index - 1]);
            const number = index + 1;
            const active = index === currentIndex;
            return (
              <li
                key={`${step.title}-${index}`}
                id={`step-${number}`}
                ref={(node) => {
                  stepRefs.current[index] = node;
                }}
                aria-current={active ? "step" : undefined}
                data-active={active || undefined}
                className="relative scroll-mt-40 list-none pl-11"
              >
                <a
                  href={`#step-${number}`}
                  aria-label={`Link to step ${number}: ${step.title}`}
                  title={`Link to step ${number}`}
                  className={`absolute left-0 top-1 flex h-9 w-9 items-center justify-center rounded-full border text-xs font-semibold tabular-nums shadow-sm transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${
                    active
                      ? "border-accent-solid bg-accent-solid text-white shadow-accent"
                      : "border-accent-soft-line bg-surface text-accent-text hover:border-accent-300 hover:bg-accent-soft"
                  }`}
                >
                  {number}
                </a>
                <details
                  open
                  className={`group overflow-hidden rounded-panel border bg-surface shadow-card transition duration-150 ${
                    active ? "border-accent-soft-line ring-2 ring-accent-500/20" : "border-line"
                  }`}
                >
                  <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-ink transition duration-150 hover:bg-surface-muted">
                    <span className="min-w-0 flex-1">{step.title}</span>
                    {active && (
                      <span className="shrink-0 rounded-pill bg-accent-soft px-2 py-0.5 text-2xs font-semibold text-accent-text">
                        current
                      </span>
                    )}
                    {changed.length > 0 && (
                      <span className="shrink-0 rounded-pill bg-warning-soft px-2 py-0.5 text-2xs font-semibold text-warning">
                        updated
                      </span>
                    )}
                    <Icon
                      name="chevronDown"
                      size={15}
                      className="shrink-0 text-ink-subtle transition duration-150 group-open:rotate-180"
                    />
                  </summary>
                  <div className="space-y-2.5 border-t border-line px-4 py-3.5">
                    {changed.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 rounded-control border border-warning/20 bg-warning-soft px-2.5 py-1.5">
                        <Icon name="refresh" size={12} className="shrink-0 text-warning" />
                        <span className="text-2xs font-semibold uppercase tracking-wide text-warning">
                          New values
                        </span>
                        <span className="font-mono text-xs tabular-nums text-ink">
                          {changed.join(" · ")}
                        </span>
                      </div>
                    )}
                    {step.latex && (
                      <div className="overflow-x-auto">
                        <LatexView latex={step.latex} display />
                      </div>
                    )}
                    {step.note && (
                      <p className="text-xs leading-relaxed text-ink-muted">{step.note}</p>
                    )}
                  </div>
                </details>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
