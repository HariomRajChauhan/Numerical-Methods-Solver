import { Link, useParams } from "react-router-dom";

import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { MethodStatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Icon } from "../components/ui/Icon";
import { usePageTitle } from "../hooks/usePageTitle";
import { selectChapter, selectChapterMethods, useCatalogStore } from "../store/catalog";
import { chapterVisual } from "../utils/chapters";
import { ui } from "../utils/ui";
import { NotFoundPage } from "./NotFoundPage";

/** Chapter overview: every method in the chapter, with availability status. */
export function ChapterPage() {
  const { chapterId } = useParams();
  const chapters = useCatalogStore((state) => state.chapters);
  const methods = useCatalogStore((state) => state.methods);
  const status = useCatalogStore((state) => state.status);
  const error = useCatalogStore((state) => state.error);
  const load = useCatalogStore((state) => state.load);

  const chapter = chapterId ? selectChapter(chapters, chapterId) : undefined;
  const chapterMethods = chapterId ? selectChapterMethods(methods, chapterId) : [];
  usePageTitle(
    chapter?.title ??
      (status === "error"
        ? "Chapter unavailable"
        : status === "ready" && chapterId
          ? "Page not found"
          : undefined),
  );

  if (status === "ready" && chapterId && !chapter) {
    return <NotFoundPage message="That chapter does not exist." />;
  }

  if (status === "loading" || status === "idle") {
    return (
      <div className="mx-auto min-h-[calc(100dvh-4rem)] max-w-6xl space-y-6 py-2">
        <LoadingSkeleton lines={2} />
        <div className={`p-6 ${ui.card}`}>
          <LoadingSkeleton lines={4} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className={`p-5 ${ui.card}`}>
              <LoadingSkeleton lines={3} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (status === "error" && !chapter) {
    return (
      <div className="mx-auto max-w-2xl py-12">
        <ErrorState
          title="This chapter could not load"
          error={error}
          onRetry={() => void load(true)}
          retryLabel="Reload catalogue"
        />
        <Link
          to="/"
          className="mt-5 inline-flex items-center gap-1.5 text-xs font-semibold text-accent-text transition hover:opacity-75"
        >
          <Icon name="arrowLeft" size={13} />
          Back to all chapters
        </Link>
      </div>
    );
  }

  if (!chapter) {
    return <NotFoundPage message="That chapter does not exist." />;
  }

  const visual = chapterVisual(chapter.id);
  const percent =
    chapter.method_count === 0
      ? 0
      : Math.round((chapter.available_count / chapter.method_count) * 100);
  const available = chapterMethods.filter((method) => method.status === "available").length;
  const comingSoon = chapterMethods.length - available;
  const chapterIndex = chapters.findIndex((item) => item.id === chapter.id);
  const previous = chapterIndex > 0 ? chapters[chapterIndex - 1] : undefined;
  const next = chapterIndex >= 0 ? chapters[chapterIndex + 1] : undefined;

  return (
    <div className="mx-auto max-w-6xl space-y-7">
      <nav
        aria-label="Breadcrumb"
        className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-1 rounded-md px-1 py-0.5 transition hover:text-indigo-600 dark:hover:text-indigo-300"
        >
          <Icon name="home" size={13} />
          Home
        </Link>
        <Icon name="chevronRight" size={12} className="text-slate-300 dark:text-slate-600" />
        <span>Chapters</span>
        <Icon name="chevronRight" size={12} className="text-slate-300 dark:text-slate-600" />
        <span className="truncate font-medium text-slate-700 dark:text-slate-200">
          {chapter.title}
        </span>
      </nav>

      {status === "error" && error && (
        <ErrorState
          compact
          title="Catalogue refresh failed"
          error={error}
          onRetry={() => void load(true)}
          retryLabel="Reload catalogue"
        />
      )}

      <header
        className={`relative overflow-hidden rounded-3xl border bg-white/80 p-6 shadow-sm shadow-slate-900/[0.03] sm:p-8 dark:bg-slate-900/40 dark:shadow-none ${visual.border}`}
      >
        <div
          aria-hidden="true"
          className={`absolute -right-20 -top-24 h-64 w-64 rounded-full bg-gradient-to-br ${visual.gradient} opacity-10 blur-3xl`}
        />
        <div className="relative">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex items-start gap-4">
              <span
                className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${visual.gradient} text-white shadow-lg`}
              >
                <Icon name={visual.icon} size={26} />
              </span>
              <div>
                <p
                  className={`text-[11px] font-semibold uppercase tracking-[0.16em] ${visual.accent}`}
                >
                  Chapter {chapter.number}
                </p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
                  {chapter.title}
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  {chapter.description}
                </p>
              </div>
            </div>

            <dl className="grid w-full shrink-0 grid-cols-2 gap-2 lg:w-auto">
              <div className="rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3 dark:border-white/[0.07] dark:bg-white/[0.03]">
                <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Available
                </dt>
                <dd className="mt-0.5 text-lg font-bold text-slate-900 dark:text-white">
                  {chapter.available_count}
                  <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    /{chapter.method_count}
                  </span>
                </dd>
              </div>
              <div className="rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3 dark:border-white/[0.07] dark:bg-white/[0.03]">
                <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Coverage
                </dt>
                <dd className="mt-0.5 text-lg font-bold text-slate-900 dark:text-white">
                  {percent}%
                </dd>
              </div>
            </dl>
          </div>

          <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/[0.08]">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${visual.gradient} transition-[width] duration-500`}
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      </header>

      <section aria-labelledby="chapter-methods-heading">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className={ui.sectionLabel}>Methods</p>
            <h2
              id="chapter-methods-heading"
              className="mt-1 text-xl font-bold tracking-tight text-slate-900 dark:text-white"
            >
              Choose a method
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {available} available
            {comingSoon > 0 && ` · ${comingSoon} coming soon`}
          </p>
        </div>

        {chapterMethods.length === 0 ? (
          <EmptyState
            icon="layers"
            title="No methods in this chapter yet"
            description="Methods are registered from the syllabus catalogue. Check back after the next release."
            action={
              <Link to="/" className={ui.btn}>
                <Icon name="arrowLeft" size={14} />
                Browse other chapters
              </Link>
            }
          />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {chapterMethods.map((method, index) => {
              const isAvailable = method.status === "available";
              return (
                <li key={method.id}>
                  <Link
                    to={`/methods/${method.id}`}
                    className={`group flex h-full flex-col p-5 ${ui.card} ${ui.cardHover}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <MethodStatusBadge status={method.status} />
                    </div>
                    <h3 className="mt-3 text-[15px] font-semibold text-slate-900 transition group-hover:text-indigo-700 dark:text-slate-100 dark:group-hover:text-indigo-300">
                      {method.name}
                    </h3>
                    <p className="mt-1.5 flex-1 text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">
                      {method.summary}
                    </p>
                    <span className="mt-4 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 transition group-hover:text-indigo-600 dark:text-slate-300 dark:group-hover:text-indigo-300">
                      {isAvailable ? "Open solver" : "Preview theory"}
                      <Icon
                        name="arrowRight"
                        size={13}
                        className="transition group-hover:translate-x-0.5"
                      />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {(previous || next) && (
        <nav aria-label="Chapter navigation" className="grid gap-3 sm:grid-cols-2">
          {previous ? (
            <Link to={`/chapters/${previous.id}`} className={`group flex items-center gap-3 p-4 ${ui.card} ${ui.cardHover}`}>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500 transition group-hover:bg-indigo-50 group-hover:text-indigo-600 dark:bg-white/[0.06] dark:text-slate-400 dark:group-hover:bg-indigo-500/10 dark:group-hover:text-indigo-300">
                <Icon name="arrowLeft" size={16} />
              </span>
              <span className="min-w-0">
                <span className="block text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Previous chapter
                </span>
                <span className="mt-0.5 block truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {previous.title}
                </span>
              </span>
            </Link>
          ) : (
            <span className="hidden sm:block" />
          )}
          {next && (
            <Link
              to={`/chapters/${next.id}`}
              className={`group flex items-center justify-end gap-3 p-4 text-right ${ui.card} ${ui.cardHover}`}
            >
              <span className="min-w-0">
                <span className="block text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Next chapter
                </span>
                <span className="mt-0.5 block truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {next.title}
                </span>
              </span>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500 transition group-hover:bg-indigo-50 group-hover:text-indigo-600 dark:bg-white/[0.06] dark:text-slate-400 dark:group-hover:bg-indigo-500/10 dark:group-hover:text-indigo-300">
                <Icon name="arrowRight" size={16} />
              </span>
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
