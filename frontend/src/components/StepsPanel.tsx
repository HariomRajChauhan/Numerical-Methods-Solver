import { useMemo } from "react";

import type { Step } from "../types/api";
import { ui } from "../utils/ui";
import { CopyButton } from "./CopyButton";
import { LatexView } from "./LatexView";
import { Icon } from "./ui/Icon";

interface StepsPanelProps {
  steps: Step[];
}

/** Exam-style working: numbered timeline, KaTeX-rendered, collapsible, copyable. */
export function StepsPanel({ steps }: StepsPanelProps) {
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
      <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 bg-white/50 px-6 py-12 text-center dark:border-white/10 dark:bg-white/[0.02]">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-white/[0.06] dark:text-slate-500">
          <Icon name="list" size={19} />
        </span>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No working steps were produced.
        </p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={ui.sectionLabel}>Working</p>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {steps.length} step{steps.length === 1 ? "" : "s"} · rendered with KaTeX
          </p>
        </div>
        <CopyButton text={asText} label="Copy working" />
      </div>

      <div className="relative">
        <span
          aria-hidden="true"
          className="absolute bottom-4 left-[17px] top-4 w-px bg-gradient-to-b from-indigo-200 via-slate-200 to-transparent dark:from-indigo-400/30 dark:via-white/10 dark:to-transparent"
        />
        <ol className="list-none space-y-3">
          {steps.map((step, index) => (
            <li key={`${step.title}-${index}`} className="relative list-none pl-11">
              <span className="absolute left-0 top-1 flex h-9 w-9 items-center justify-center rounded-full border border-indigo-200/80 bg-white text-xs font-semibold text-indigo-600 shadow-sm dark:border-indigo-400/25 dark:bg-slate-900 dark:text-indigo-300">
                {index + 1}
              </span>
              <details
                open
                className="group overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm shadow-slate-900/[0.03] dark:border-white/[0.07] dark:bg-slate-900/60 dark:shadow-none"
              >
                <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50/80 dark:text-slate-200 dark:hover:bg-white/[0.03]">
                  <span className="min-w-0 flex-1">{step.title}</span>
                  <Icon
                    name="chevronDown"
                    size={15}
                    className="shrink-0 text-slate-400 transition group-open:rotate-180"
                  />
                </summary>
                <div className="space-y-2 border-t border-slate-100 px-4 py-3.5 dark:border-white/[0.06]">
                  {step.latex && (
                    <div className="overflow-x-auto">
                      <LatexView latex={step.latex} display />
                    </div>
                  )}
                  {step.note && (
                    <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                      {step.note}
                    </p>
                  )}
                </div>
              </details>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
