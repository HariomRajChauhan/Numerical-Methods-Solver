import { useRef } from "react";

export interface TabDef {
  id: string;
  label: string;
  badge?: string | number;
  disabled?: boolean;
}

interface TabsProps {
  tabs: TabDef[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}

/** Accessible tab bar (role=tablist, arrow-key navigation). */
export function Tabs({ tabs, activeId, onChange, className = "" }: TabsProps) {
  const listRef = useRef<HTMLDivElement>(null);

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
      className={`flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800 ${className}`}
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
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 ${
              active
                ? "border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span className="ml-1.5 rounded-full bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
