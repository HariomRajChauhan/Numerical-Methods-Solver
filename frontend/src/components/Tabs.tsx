import { useEffect, useRef } from "react";

import { Icon, type IconName } from "./ui/Icon";

export interface TabDef {
  id: string;
  label: string;
  icon?: IconName;
  badge?: string | number;
  disabled?: boolean;
}

interface TabsProps {
  tabs: TabDef[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}

/** Accessible tab bar (underline style, no outer box, AA contrast). */
export function Tabs({ tabs, activeId, onChange, className = "" }: TabsProps) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [activeId]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>): void {
    const enabled = tabs.filter((tab) => !tab.disabled);
    const index = enabled.findIndex((tab) => tab.id === activeId);
    if (index < 0) return;
    let next: number;
    switch (event.key) {
      case "ArrowRight":
        next = (index + 1) % enabled.length;
        break;
      case "ArrowLeft":
        next = (index - 1 + enabled.length) % enabled.length;
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = enabled.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    onChange(enabled[next].id);
    const buttons = listRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    buttons?.[next]?.focus();
  }

  return (
    <div
      ref={listRef}
      role="tablist"
      aria-label="Solution views"
      onKeyDown={handleKeyDown}
      className={`no-scrollbar relative flex items-center gap-4 overflow-x-auto border-b border-[color:var(--color-border)] px-1 ${className}`}
    >
      {tabs.map((tab) => {
        const active = tab.id === activeId;
        return (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={active}
            aria-controls={`panel-${tab.id}`}
            disabled={tab.disabled}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.id)}
            className={`relative flex shrink-0 items-center gap-1.5 py-3 text-sm font-medium transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-40 ${
              active
                ? "text-[color:var(--color-text)] font-semibold"
                : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]"
            }`}
          >
            {tab.icon && <Icon name={tab.icon} size={15} />}
            {tab.label}
            {tab.badge !== undefined && (
              <span className="ml-1 rounded-full bg-[color:var(--color-surface-2)] px-2 py-0.5 text-[10px] font-semibold tabular-nums text-[color:var(--color-text-muted)]">
                {tab.badge}
              </span>
            )}
            {active && (
              <span
                aria-hidden="true"
                className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t bg-[color:var(--color-accent)]"
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
