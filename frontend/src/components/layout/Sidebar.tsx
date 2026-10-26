import { NavLink, useParams } from "react-router-dom";

import { selectChapterMethods, useCatalogStore } from "../../store/catalog";
import { chapterVisual } from "../../utils/chapters";
import { ui } from "../../utils/ui";
import { LoadingSkeleton } from "../LoadingSkeleton";
import { Icon } from "../ui/Icon";

interface SidebarProps {
  /** Called after navigation on mobile (to close the drawer). */
  onNavigate?: () => void;
}

/** Collapsible Chapter → Method navigation tree built from the catalogue. */
export function Sidebar({ onNavigate }: SidebarProps) {
  const { chapterId, methodId } = useParams();
  const chapters = useCatalogStore((state) => state.chapters);
  const methods = useCatalogStore((state) => state.methods);
  const status = useCatalogStore((state) => state.status);

  if (status === "loading" || status === "idle") {
    return (
      <div className="space-y-4 px-4 py-5">
        <LoadingSkeleton lines={2} />
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  const available = methods.filter((method) => method.status === "available").length;
  const total = methods.length;
  const percent = total === 0 ? 0 : Math.round((available / total) * 100);

  return (
    <nav aria-label="Syllabus" className="flex min-h-full flex-col gap-5 px-3 py-4">
      <div className="rounded-2xl border border-indigo-200/60 bg-gradient-to-br from-indigo-50 via-white to-white p-3.5 dark:border-indigo-400/15 dark:from-indigo-500/[0.08] dark:via-transparent dark:to-transparent">
        <div className="flex items-center justify-between gap-2">
          <p className={ui.sectionLabel}>Course progress</p>
          <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-indigo-600 ring-1 ring-inset ring-indigo-200/70 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20">
            {percent}%
          </span>
        </div>
        <p className="mt-1.5 text-sm font-semibold text-slate-800 dark:text-slate-100">
          {available} of {total} methods ready
        </p>
        <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-slate-200/80 dark:bg-white/[0.08]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-[width] duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
          {total - available} syllabus method{total - available === 1 ? "" : "s"} coming soon
        </p>
      </div>

      <div className="space-y-1">
        <p className={`px-2 pb-1 ${ui.sectionLabel}`}>Chapters</p>
        {chapters.map((chapter) => {
          const chapterMethods = selectChapterMethods(methods, chapter.id);
          const expanded =
            chapterId === chapter.id || chapterMethods.some((method) => method.id === methodId);
          const visual = chapterVisual(chapter.id);
          return (
            <details key={chapter.id} open={expanded} className="group">
              <summary className="flex cursor-pointer list-none items-center gap-2.5 rounded-xl px-2 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100/80 dark:text-slate-200 dark:hover:bg-white/[0.04]">
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${visual.tint}`}
                >
                  <Icon name={visual.icon} size={15} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate leading-tight">{chapter.title}</span>
                  <span className="block text-[10px] font-normal text-slate-600 dark:text-slate-400">
                    Chapter {chapter.number} · {chapter.available_count}/{chapter.method_count}
                  </span>
                </span>
                <Icon
                  name="chevronDown"
                  size={14}
                  className="shrink-0 text-slate-400 transition group-open:rotate-180"
                />
              </summary>

              <ul className="ml-3.5 mt-1 space-y-0.5 border-l border-slate-200/80 pl-2.5 dark:border-white/[0.06]">
                <li>
                  <NavLink
                    to={`/chapters/${chapter.id}`}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      `block rounded-lg px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-wide transition ${
                        isActive
                          ? "text-indigo-600 dark:text-indigo-300"
                          : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
                      }`
                    }
                  >
                    Chapter overview
                  </NavLink>
                </li>
                {chapterMethods.map((method) => (
                  <li key={method.id}>
                    <NavLink
                      to={`/methods/${method.id}`}
                      onClick={onNavigate}
                      title={method.summary}
                      className={({ isActive }) =>
                        `flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] transition ${
                          isActive
                            ? "bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-200"
                            : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/[0.04] dark:hover:text-white"
                        }`
                      }
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
        })}
      </div>

      <div className="mt-auto space-y-0.5 border-t border-slate-200/80 pt-3 dark:border-white/[0.06]">
        <NavLink
          to="/"
          end
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium transition ${
              isActive
                ? "bg-slate-100 text-slate-900 dark:bg-white/[0.06] dark:text-white"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
            }`
          }
        >
          <Icon name="home" size={15} />
          Home
        </NavLink>
        <NavLink
          to="/about"
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium transition ${
              isActive
                ? "bg-slate-100 text-slate-900 dark:bg-white/[0.06] dark:text-white"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
            }`
          }
        >
          <Icon name="info" size={15} />
          About
        </NavLink>
      </div>
    </nav>
  );
}
