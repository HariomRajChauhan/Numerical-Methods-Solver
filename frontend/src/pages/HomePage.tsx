import { Link } from "react-router-dom";

import { ErrorAlert } from "../components/ErrorAlert";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { useCatalogStore } from "../store/catalog";
import { ui } from "../utils/ui";

/** Landing page: hero + six syllabus chapter cards. */
export function HomePage() {
  const chapters = useCatalogStore((state) => state.chapters);
  const status = useCatalogStore((state) => state.status);
  const error = useCatalogStore((state) => state.error);
  const load = useCatalogStore((state) => state.load);

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-indigo-50 via-white to-white p-6 sm:p-10 dark:border-slate-800 dark:from-indigo-950/40 dark:via-slate-900 dark:to-slate-900">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-slate-50">
          Numerical Methods Solver
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base dark:text-slate-300">
          Pick a chapter, pick a method, enter your problem and get the answer, exam-style
          step-by-step working, interactive graphs, error and convergence information, plus a
          downloadable report.
        </p>
        <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
          Use the search bar above to jump straight to a method (try “Newton” or “Simpson”).
        </p>
      </section>

      {status === "error" && error && (
        <ErrorAlert error={error} onDismiss={() => void load(true)} />
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-800 dark:text-slate-100">Chapters</h2>
        {status === "loading" || status === "idle" ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <div key={index} className={`p-5 ${ui.card}`}>
                <LoadingSkeleton lines={3} />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {chapters.map((chapter) => (
              <Link
                key={chapter.id}
                to={`/chapters/${chapter.id}`}
                className={`flex flex-col p-5 ${ui.card} ${ui.cardHover}`}
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
                  {chapter.number}
                </span>
                <h3 className="mt-3 font-semibold text-slate-900 dark:text-slate-100">
                  {chapter.title}
                </h3>
                <p className="mt-1 flex-1 text-sm text-slate-600 dark:text-slate-400">
                  {chapter.description}
                </p>
                <p className="mt-3 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {chapter.available_count} of {chapter.method_count} methods available
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
