import type { ReactNode } from "react";

import { CopyButton } from "./CopyButton";
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

/** Dark code block with line numbers, labelled header, copy button and per-theme syntax tokens. */
export function CodePanel({
  title,
  icon = "code",
  language,
  code,
  emptyMessage = "Nothing to show yet.",
  actions,
}: CodePanelProps) {
  const lines = code.trim() ? code.trim().split("\n") : [];

  return (
    <section className={`overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[color:var(--color-border)] px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name={icon} size={14} />
          </span>
          <h2 className="truncate text-sm font-semibold text-[color:var(--color-text)]">{title}</h2>
          {language && (
            <span className="rounded-md bg-[color:var(--color-surface-2)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">
              {language}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {lines.length > 0 && <CopyButton text={code.trim()} label="Copy code" />}
          {actions}
        </div>
      </header>

      {lines.length > 0 ? (
        <div className="relative">
          <div
            aria-hidden="true"
            className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[color:color-mix(in_oklab,var(--color-accent)_40%,transparent)] to-transparent"
          />
          <pre
            role="region"
            tabIndex={0}
            aria-label={`${title} code`}
            className="max-h-[36rem] overflow-auto bg-[color:var(--color-surface-2)] p-0 font-mono text-xs leading-relaxed text-[color:var(--color-text)] scroll-slim focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[color:var(--color-accent)]"
          >
            <table className="w-full border-collapse" role="presentation">
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i} className="hover:bg-[color:color-mix(in_oklab,var(--color-accent)_5%,transparent)]">
                    <td
                      aria-hidden="true"
                      className="select-none border-r border-[color:var(--color-border)] px-3 py-0.5 text-right text-[color:var(--color-text-subtle)] opacity-50"
                      style={{ minWidth: "3rem" }}
                    >
                      {i + 1}
                    </td>
                    <td className="px-4 py-0.5 whitespace-pre">
                      <code>{line}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </pre>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-1)] bg-[color:var(--color-surface-2)] text-[color:var(--color-text-subtle)]">
            <Icon name={icon} size={19} />
          </span>
          <p className="text-sm text-[color:var(--color-text-muted)]">{emptyMessage}</p>
        </div>
      )}
    </section>
  );
}
