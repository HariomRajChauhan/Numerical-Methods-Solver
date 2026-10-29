import { useState } from "react";
import { NavLink } from "react-router-dom";

import type { ChapterInfo, MethodMeta } from "../../types/api";
import { selectChapterMethods } from "../../store/catalog";
import { chapterVisual } from "../../utils/chapters";
import { Icon } from "../ui/Icon";

interface SidebarChapterProps {
  chapter: ChapterInfo;
  methods: MethodMeta[];
  activeChapterId: string | undefined;
  activeMethodId: string | undefined;
  isRail: boolean;
  onChapterClick: (id: string) => void;
  onMethodClick: (id: string) => void;
  onNavigate?: () => void;
}

/** Single chapter accordion: icon-only in rail, full tree in expanded. */
export function SidebarChapter({
  chapter,
  methods,
  activeChapterId,
  activeMethodId,
  isRail,
  onChapterClick,
  onMethodClick,
  onNavigate,
}: SidebarChapterProps) {
  const visual = chapterVisual(chapter.id);
  const [expanded, setExpanded] = useState(activeChapterId === chapter.id);

  const chapterMethods = expanded ? selectChapterMethods(methods, chapter.id) : [];

  const isActiveChapter = activeChapterId === chapter.id;

  if (isRail) {
    return (
      <button
        type="button"
        aria-label={chapter.title}
        aria-expanded={expanded}
        aria-current={isActiveChapter ? "true" : undefined}
        onClick={() => {
          onChapterClick(chapter.id);
          setExpanded((prev) => !prev);
        }}
        className={`flex shrink-0 items-center justify-center rounded-xl p-2 transition ${
          isActiveChapter
            ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300"
            : "text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
        }`}
        title={chapter.title}
      >
        <Icon name={visual.icon} size={18} />
      </button>
    );
  }

  return (
    <details
      key={chapter.id}
      open={expanded || isActiveChapter}
      onToggle={(event) => setExpanded(event.currentTarget.open)}
      className="group"
    >
      <summary
        className="flex cursor-pointer list-none items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100/80 dark:text-slate-200 dark:hover:bg-white/[0.04]"
        onClick={(event) => {
          event.preventDefault();
          setExpanded((prev) => !prev);
        }}
      >
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${visual.tint}`}
        >
          <Icon name={visual.icon} size={16} />
        </span>
        <div className="min-w-0 flex-1 overflow-hidden">
          <span className="block truncate leading-tight">{chapter.title}</span>
          <span className="block text-[10px] font-normal text-slate-600 dark:text-slate-400">
            Chapter {chapter.number} · {chapter.available_count}/{chapter.method_count}
          </span>
        </div>
        <Icon
          name="chevronDown"
          size={14}
          className={`shrink-0 text-slate-400 transition ${
            expanded || isActiveChapter ? "rotate-180" : ""
          }`}
        />
      </summary>

      <ul className="ml-3.5 mt-1 space-y-0.5 border-l border-slate-200/80 pl-2.5 dark:border-white/[0.06]">
        <li>
          <NavLink
            to={`/chapters/${chapter.id}`}
            onClick={onNavigate}
            className="block rounded-lg px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-wide transition text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04]"
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
                onNavigate?.();
              }}
              title={method.summary}
              className={({ isActive }) =>
                `flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] transition ${
                  isActive
                    ? "bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-200"
                    : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/[0.04] dark:hover:text-white"
                }`
              }
              aria-current={activeMethodId === method.id ? "page" : undefined}
            >
              <span className="min-w-0 flex-1 truncate">{method.name}</span>
              {method.status === "coming_soon" && (
                <>
                  <Icon
                    name="clock"
                    size={12}
                    className="shrink-0 text-slate-400 dark:text-slate-500"
                  />
                  <span className="sr-only">Coming soon</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </details>
  );
}
