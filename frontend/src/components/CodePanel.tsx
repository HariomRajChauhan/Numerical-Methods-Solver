import type { ReactNode } from "react";

import { ui } from "../utils/ui";
import { Icon, type IconName } from "./ui/Icon";

interface CodePanelProps {
  title: string;
  icon?: IconName;
  language?: string;
  code: string;
  emptyMessage?: string;
  /** Buttons rendered on the right side of the panel header. */
  actions?: ReactNode;
}

/** Dark code block with a labelled header and optional copy/download actions. */
export function CodePanel({
  title,
  icon = "code",
  language,
  code,
  emptyMessage = "Nothing to show yet.",
  actions,
}: CodePanelProps) {
  return (
    <section className={`overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name={icon} size={14} />
          </span>
          <h2 className="truncate text-sm font-semibold text-ink">{title}</h2>
          {language && (
            <span className="rounded-md bg-surface-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-ink-muted">
              {language}
            </span>
          )}
        </div>
        {actions && <div className="flex items-center gap-1">{actions}</div>}
      </header>

      {code.trim() ? (
        <div className="relative">
          <div
            aria-hidden="true"
            className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent-400/40 to-transparent"
          />
          <pre
            role="region"
            tabIndex={0}
            aria-label={`${title} code`}
            className="max-h-[36rem] overflow-auto bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-200 scroll-slim focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-400"
          >
            <code>{code}</code>
          </pre>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-control bg-surface-muted text-ink-subtle">
            <Icon name={icon} size={19} />
          </span>
          <p className="text-sm text-ink-muted">{emptyMessage}</p>
        </div>
      )}
    </section>
  );
}
