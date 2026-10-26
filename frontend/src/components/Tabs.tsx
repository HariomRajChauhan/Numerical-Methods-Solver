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

/** Accessible tab bar (role=tablist, arrow-key navigation, scrollable on mobile). */
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
      className={`no-scrollbar flex gap-1 overflow-x-auto rounded-control border border-line bg-surface/80 p-1 backdrop-blur-sm ${className}`}
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
            className={`flex shrink-0 items-center gap-1.5 rounded-control px-3 py-2 text-[13px] font-medium transition duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 disabled:cursor-not-allowed disabled:opacity-40 ${
              active
                ? "bg-accent-solid text-white shadow-sm"
                : "text-ink-muted hover:bg-surface-muted hover:text-ink"
            }`}
          >
            {tab.icon && <Icon name={tab.icon} size={14} />}
            {tab.label}
            {tab.badge !== undefined && (
              <span
                className={`ml-0.5 rounded-md px-1.5 py-0.5 text-[10px] font-semibold tabular-nums ${
                  active ? "bg-white text-accent-700" : "bg-surface-muted text-ink-muted"
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
