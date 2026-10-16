import { NavLink, useParams } from "react-router-dom";

import { selectChapterMethods, useCatalogStore } from "../../store/catalog";
import { MethodStatusBadge } from "../StatusBadge";

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
    return <p className="px-3 py-2 text-sm text-slate-500">Loading syllabus…</p>;
  }

  return (
    <nav aria-label="Syllabus" className="space-y-1">
      {chapters.map((chapter) => {
        const chapterMethods = selectChapterMethods(methods, chapter.id);
        const expanded = chapterId === chapter.id || chapterMethods.some((m) => m.id === methodId);
        return (
          <details key={chapter.id} open={expanded} className="group">
            <summary className="flex cursor-pointer list-none items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800">
              <span className="flex items-center gap-2">
                <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-indigo-100 text-xs font-semibold text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300">
                  {chapter.number}
                </span>
                {chapter.title}
              </span>
              <span
                aria-hidden="true"
                className="text-slate-400 transition group-open:rotate-90"
              >
                ▸
              </span>
            </summary>
            <ul className="mt-0.5 space-y-0.5 pl-7">
              <li>
                <NavLink
                  to={`/chapters/${chapter.id}`}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `block rounded-md px-2 py-1 text-xs text-slate-500 transition hover:text-slate-800 dark:hover:text-slate-200 ${
                      isActive ? "text-indigo-600 dark:text-indigo-400" : ""
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
                      `flex items-center justify-between gap-1 rounded-md px-2 py-1 text-sm transition ${
                        isActive
                          ? "bg-indigo-50 font-medium text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                      }`
                    }
                  >
                    <span className="truncate">{method.name}</span>
                    {method.status === "coming_soon" && (
                      <span className="shrink-0">
                        <MethodStatusBadge status="coming_soon" />
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </details>
        );
      })}
    </nav>
  );
}
