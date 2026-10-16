import { useMemo } from "react";

import type { Step } from "../types/api";
import { CopyButton } from "./CopyButton";
import { LatexView } from "./LatexView";

interface StepsPanelProps {
  steps: Step[];
}

/** Exam-style working: numbered, KaTeX-rendered, collapsible, copyable. */
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
    return <p className="text-sm text-slate-500">No working steps were produced.</p>;
  }

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <CopyButton text={asText} label="Copy working" />
      </div>
      <ol className="space-y-3">
        {steps.map((step, index) => (
          <li key={`${step.title}-${index}`} className="list-none">
            <details open className="group rounded-xl border border-slate-200 dark:border-slate-800">
              <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800/60">
                <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300">
                  {index + 1}
                </span>
                <span className="flex-1">{step.title}</span>
                <span aria-hidden="true" className="text-slate-400 transition group-open:rotate-180">
                  ⌄
                </span>
              </summary>
              <div className="space-y-2 border-t border-slate-100 px-4 py-3 dark:border-slate-800">
                {step.latex && (
                  <div className="overflow-x-auto">
                    <LatexView latex={step.latex} display />
                  </div>
                )}
                {step.note && <p className="text-xs text-slate-500 dark:text-slate-400">{step.note}</p>}
              </div>
            </details>
          </li>
        ))}
      </ol>
    </div>
  );
}
