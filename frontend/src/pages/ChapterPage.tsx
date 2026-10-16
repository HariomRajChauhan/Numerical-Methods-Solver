import { Link, useParams } from "react-router-dom";

import { MethodStatusBadge } from "../components/StatusBadge";
import { NotFoundPage } from "./NotFoundPage";
import { selectChapter, selectChapterMethods, useCatalogStore } from "../store/catalog";
import { ui } from "../utils/ui";

/** Chapter overview: every method in the chapter, with availability status. */
export function ChapterPage() {
  const { chapterId } = useParams();
  const chapters = useCatalogStore((state) => state.chapters);
  const methods = useCatalogStore((state) => state.methods);
  const status = useCatalogStore((state) => state.status);

  if (status === "ready" && chapterId && !selectChapter(chapters, chapterId)) {
    return <NotFoundPage message="That chapter does not exist." />;
  }

  const chapter = chapterId ? selectChapter(chapters, chapterId) : undefined;
  const chapterMethods = chapterId ? selectChapterMethods(methods, chapterId) : [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <nav aria-label="Breadcrumb" className="text-xs text-slate-500">
        <Link to="/" className="hover:text-indigo-600 dark:hover:text-indigo-400">
          Home
        </Link>
        <span aria-hidden="true"> / </span>
        <span>Chapter {chapter?.number ?? ""}</span>
      </nav>

      <header>
        <h1 className="text-xl font-bold text-slate-900 dark:text-slate-50">
          {chapter?.title ?? "Chapter"}
        </h1>
        {chapter && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{chapter.description}</p>
        )}
      </header>

      <ul className="grid gap-3 sm:grid-cols-2">
        {chapterMethods.map((method) => {
          const available = method.status === "available";
          return (
            <li key={method.id}>
              <Link
                to={`/methods/${method.id}`}
                className={`block p-4 ${ui.card} ${ui.cardHover} ${
                  available ? "" : "opacity-80"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                    {method.name}
                  </h2>
                  <MethodStatusBadge status={method.status} />
                </div>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  {method.summary}
                </p>
              </Link>
            </li>
          );
        })}
        {chapterMethods.length === 0 && (
          <li className="text-sm text-slate-500">No methods are registered for this chapter yet.</li>
        )}
      </ul>
    </div>
  );
}
