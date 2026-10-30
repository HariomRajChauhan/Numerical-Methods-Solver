import { useEffect, useMemo, useRef, useState } from "react";

import { useReducedMotion } from "../hooks/useReducedMotion";
import type { Step } from "../types/api";
import { copyText } from "../utils/download";
import { ui } from "../utils/ui";
import { CopyButton } from "./CopyButton";
import { IterationPlayer } from "./IterationPlayer";
import { LatexView } from "./LatexView";
import { EmptyState } from "./ui/EmptyState";
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

function stepToText(step: Step, number: number): string {
  const parts = [`${number}. ${step.title}`];
  if (step.latex) parts.push(`   ${step.latex}`);
  if (step.note) parts.push(`   (${step.note})`);
  return parts.join("\n");
}

/** Exam-style working: numbered timeline, anchor links, KaTeX, collapsible cards. */
export function StepsPanel({ steps }: StepsPanelProps) {
  const [activeIndex, setActiveIndex] = useState(() => Math.max(0, steps.length - 1));
  const [allOpen, setAllOpen] = useState(true);
  const stepRefs = useRef<(HTMLLIElement | null)[]>([]);
  const detailsRefs = useRef<(HTMLDetailsElement | null)[]>([]);
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
    () => steps.map((step, index) => stepToText(step, index + 1)).join("\n\n"),
    [steps],
  );

  function expandAll(): void {
    detailsRefs.current.forEach((el) => { if (el) el.open = true; });
    setAllOpen(true);
  }

  function collapseAll(): void {
    detailsRefs.current.forEach((el) => { if (el) el.open = false; });
    setAllOpen(false);
  }

  if (steps.length === 0) {
    return (
      <EmptyState
        icon="list"
        title="No working steps"
        description="This method did not produce a step-by-step derivation."
      />
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
          <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
            <span className="tabular-nums">{steps.length}</span> step
            {steps.length === 1 ? "" : "s"} · rendered with KaTeX
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={allOpen ? collapseAll : expandAll}
            className={ui.btnGhost}
            aria-label={allOpen ? "Collapse all steps" : "Expand all steps"}
          >
            <Icon name={allOpen ? "chevronUp" : "chevronDown"} size={13} />
            {allOpen ? "Collapse all" : "Expand all"}
          </button>
          <CopyButton text={asText} label="Copy working" />
        </div>
      </div>

      <div className="relative">
        <span
          aria-hidden="true"
          className="absolute bottom-4 left-[17px] top-4 w-px bg-gradient-to-b from-[color:color-mix(in_oklab,var(--color-accent)_30%,transparent)] via-[color:var(--color-border)] to-transparent"
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
                  className={`absolute left-0 top-1 flex h-9 w-9 items-center justify-center rounded-full border text-xs font-semibold tabular-nums transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] ${
                    active
                      ? "border-[color:var(--color-accent)] bg-[color:var(--color-accent)] text-white"
                      : "border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-accent)] hover:bg-[color:var(--color-accent-soft)]"
                  }`}
                >
                  {number}
                </a>
                <details
                  open={allOpen}
                  ref={(node) => {
                    detailsRefs.current[index] = node;
                  }}
                  className={`group overflow-hidden rounded-[var(--radius-2)] border bg-[color:var(--color-surface)] transition duration-150 ${
                    active
                      ? "border-[color:color-mix(in_oklab,var(--color-accent)_30%,transparent)] ring-2 ring-[color:color-mix(in_oklab,var(--color-accent)_20%,transparent)]"
                      : "border-[color:var(--color-border)]"
                  }`}
                >
                  <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-[color:var(--color-text)] transition duration-150 hover:bg-[color:var(--color-surface-2)]">
                    <span className="min-w-0 flex-1">{step.title}</span>
                    {active && (
                      <span className="shrink-0 rounded-full bg-[color:var(--color-accent-soft)] px-2 py-0.5 text-2xs font-semibold text-[color:var(--color-accent)]">
                        current
                      </span>
                    )}
                    {changed.length > 0 && (
                      <span className="shrink-0 rounded-full bg-[color:var(--color-warning-soft)] px-2 py-0.5 text-2xs font-semibold text-[color:var(--color-warning)]">
                        updated
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        void copyText(stepToText(step, number));
                      }}
                      className="shrink-0 rounded-md p-1 text-[color:var(--color-text-subtle)] opacity-0 transition duration-150 hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-text)] group-hover:opacity-100 focus:opacity-100"
                      aria-label={`Copy step ${number}`}
                      title="Copy step"
                    >
                      <Icon name="copy" size={12} />
                    </button>
                    <Icon
                      name="chevronDown"
                      size={15}
                      className="shrink-0 text-[color:var(--color-text-subtle)] transition duration-150 group-open:rotate-180"
                    />
                  </summary>
                  <div className="max-h-80 space-y-2.5 overflow-y-auto scroll-slim border-t border-[color:var(--color-border)] px-4 py-3.5">
                    {changed.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 rounded-[var(--radius-1)] border border-[color:color-mix(in_oklab,var(--color-warning)_20%,transparent)] bg-[color:var(--color-warning-soft)] px-2.5 py-1.5">
                        <Icon name="refresh" size={12} className="shrink-0 text-[color:var(--color-warning)]" />
                        <span className="text-2xs font-semibold uppercase tracking-wide text-[color:var(--color-warning)]">
                          New values
                        </span>
                        <span className="font-mono text-xs tabular-nums text-[color:var(--color-text)]">
                          {changed.join(" · ")}
                        </span>
                      </div>
                    )}
                    {step.latex && (
                      <div className="overflow-x-auto text-base leading-relaxed">
                        <LatexView latex={step.latex} display />
                      </div>
                    )}
                    {step.note && (
                      <p className="text-xs leading-relaxed text-[color:var(--color-text-muted)]">{step.note}</p>
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
