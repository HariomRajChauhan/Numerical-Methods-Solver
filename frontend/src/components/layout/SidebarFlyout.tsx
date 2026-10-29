import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";

import type { ChapterInfo, MethodMeta } from "../../types/api";
import { selectChapterMethods } from "../../store/catalog";
import { chapterVisual } from "../../utils/chapters";
import { Icon } from "../ui/Icon";

interface SidebarFlyoutProps {
  chapter: ChapterInfo | null;
  methods: MethodMeta[];
  activeMethodId: string | undefined;
  isOpen: boolean;
  onClose: () => void;
  onMethodClick: (id: string) => void;
}

/**
 * Flyout panel shown beside the rail when a chapter icon is clicked.
 * Lists that chapter's methods; closes on selection, Escape or outside click.
 */
export function SidebarFlyout({
  chapter,
  methods,
  activeMethodId,
  isOpen,
  onClose,
  onMethodClick,
}: SidebarFlyoutProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState(false);

  const chapterMethods = chapter
    ? selectChapterMethods(methods, chapter.id)
    : [];

  const visual = chapter ? chapterVisual(chapter.id) : undefined;

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !chapter || !visual) return null;

  return (
    <div
      ref={containerRef}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`fixed top-16 z-40 w-[260px] overflow-y-auto border border-line-strong bg-surface shadow-popover scroll-slim transition-opacity duration-200 ${
        hovered ? "opacity-100" : "opacity-90"
      } dark:border-white/[0.16] dark:bg-[#0f172a] scroll-slim`}
      style={{
        left: "56px",
        height: `calc(100dvh - 4rem)`,
      }}
    >
      <div className="flex items-center gap-2.5 rounded-xl border-b border-line px-3 py-2.5 dark:border-white/[0.06]">
        <span
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${visual.tint}`}
        >
          <Icon name={visual.icon} size={15} />
        </span>
        <div className="min-w-0 flex-1 overflow-hidden">
          <p className="text-xs font-semibold text-ink leading-tight">{chapter.title}</p>
          <p className="text-[10px] text-ink-muted">
            Chapter {chapter.number} · {chapter.available_count}/{chapter.method_count} methods
          </p>
        </div>
      </div>

      <nav aria-label={`${chapter.title} methods`} className="py-1">
        <ul className="space-y-0.5">
          <li>
            <NavLink
              to={`/chapters/${chapter.id}`}
              onClick={(event) => {
                event.preventDefault();
                onMethodClick(chapter.id);
              }}
              className="block rounded-lg px-3 py-2 text-[11px] font-medium uppercase tracking-wide transition hover:bg-surface-muted dark:hover:bg-white/[0.04]"
            >
              Chapter overview
            </NavLink>
          </li>
          {chapterMethods.map((method) => (
            <li key={method.id}>
              <NavLink
                to={`/methods/${method.id}`}
                onClick={() => {
                  onMethodClick(method.id);
                }}
                title={method.summary}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-lg px-3 py-2 text-[12px] transition ${
                    isActive
                      ? "bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-200"
                      : "text-slate-600 hover:bg-surface-muted hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/[0.04] dark:hover:text-white"
                  }`
                }
                aria-current={activeMethodId === method.id ? "page" : undefined}
              >
                <span className="min-w-0 flex-1 truncate">{method.name}</span>
                {method.status === "coming_soon" && (
                  <>
                    <Icon
                      name="clock"
                      size={11}
                      className="shrink-0 text-slate-400 dark:text-slate-500"
                    />
                    <span className="sr-only">Coming soon</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
          {chapterMethods.length === 0 && (
            <li>
              <p className="px-3 py-2 text-[11px] text-ink-subtle">
                No methods in this chapter yet.
              </p>
            </li>
          )}
        </ul>
      </nav>
    </div>
  );
}
