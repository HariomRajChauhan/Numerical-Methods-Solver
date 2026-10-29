import { Link } from "react-router-dom";

import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Icon, type IconName } from "../components/ui/Icon";
import { usePageTitle } from "../hooks/usePageTitle";
import { useCatalogStore } from "../store/catalog";
import { chapterVisual } from "../utils/chapters";
import { ui } from "../utils/ui";

const FEATURES: { icon: IconName; title: string; text: string }[] = [
  {
    icon: "list",
    title: "Exam-style working",
    text: "Every iteration written out in rendered LaTeX — ready to copy into your answer sheet.",
  },
  {
    icon: "chart",
    title: "Interactive graphs",
    text: "Zoom, pan and inspect curves, roots and convergence without leaving the page.",
  },
  {
    icon: "file",
    title: "One-click reports",
    text: "Download a formatted PDF or a clean CSV of the iteration table for your lab file.",
  },
  {
    icon: "shield",
    title: "Safe by design",
    text: "Formulas are parsed with a whitelist — nothing you type is ever executed as code.",
  },
];

const POPULAR_METHODS = [
  { id: "newton_raphson", name: "Newton–Raphson" },
  { id: "simpson_13", name: "Simpson 1/3" },
  { id: "runge_kutta_4", name: "Runge–Kutta 4" },
  { id: "lagrange", name: "Lagrange" },
  { id: "gauss_seidel", name: "Gauss–Seidel" },
];

/** Keep the hero and closing call-to-action stable while the catalogue loads. */
const STARTER_METHOD = { id: "bisection", name: "Bisection Method" };

/** Landing page: hero, feature overview and the six syllabus chapter cards. */
export function HomePage() {
  usePageTitle();

  return (
    <div className="mx-auto max-w-6xl space-y-10 sm:space-y-12">
      <section className="hero-glow relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-xl shadow-slate-900/[0.04] sm:p-9 lg:p-12 dark:border-white/[0.07] dark:bg-slate-900/40 dark:shadow-none">
        <div aria-hidden="true" className="bg-grid absolute inset-0 opacity-80" />

        <div className="relative grid items-center gap-10 lg:grid-cols-[1.08fr_0.92fr]">
          <div className="animate-fade-up">
            <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200/80 bg-white/80 px-3 py-1.5 text-[11px] font-semibold text-indigo-700 shadow-sm backdrop-blur dark:border-indigo-400/20 dark:bg-indigo-500/10 dark:text-indigo-200">
              <Icon name="cap" size={13} />
              ENSH 252 · IOE / Tribhuvan University
            </span>

            <h1 className="mt-5 text-balance text-4xl font-extrabold leading-[1.04] tracking-tight text-slate-900 sm:text-5xl lg:text-[3.35rem] dark:text-white">
              Numerical methods,{" "}
              <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-teal-500 bg-clip-text text-transparent dark:from-indigo-400 dark:via-violet-400 dark:to-teal-300">
                solved step by step.
              </span>
            </h1>

            <p className="mt-4 max-w-xl text-pretty text-sm leading-relaxed text-slate-600 sm:text-base dark:text-slate-300">
              Pick a chapter, enter your problem and get the final answer, exam-style working,
              iteration tables, an interactive graph, convergence details and a downloadable
              report.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-2.5">
              <a href="#chapters" className={ui.btnPrimary}>
                <Icon name="bookOpen" size={16} />
                Explore chapters
                <Icon name="arrowRight" size={15} />
              </a>
              <Link to={`/methods/${STARTER_METHOD.id}`} className={ui.btn}>
                <Icon name="play" size={14} />
                Try {STARTER_METHOD.name.replace(/ Method$/, "")}
              </Link>
            </div>

            <CatalogueStats />

            <div className="mt-5 flex min-h-7 flex-wrap items-center gap-1.5">
              <span className="mr-1 text-[11px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Popular
              </span>
              {POPULAR_METHODS.map((method) => (
                <Link key={method.id} to={`/methods/${method.id}`} className={ui.chip}>
                  {method.name}
                  <Icon name="arrowUpRight" size={12} />
                </Link>
              ))}
            </div>
          </div>

          <SamplePreview />
        </div>
      </section>

      <section aria-label="What you get" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((feature, index) => (
          <div
            key={feature.title}
            className={`animate-fade-up p-4 ${ui.card} stagger-${index + 1}`}
          >
            <span className={`${ui.iconBox} h-9 w-9`}>
              <Icon name={feature.icon} size={17} />
            </span>
            <h2 className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-100">
              {feature.title}
            </h2>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              {feature.text}
            </p>
          </div>
        ))}
      </section>

      <ChapterCatalogue />

      <section className="cta-glow relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-xl shadow-slate-900/20 sm:p-8 dark:border-white/10 dark:bg-slate-900/80">
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-indigo-300">
              Start here
            </p>
            <h2 className="mt-1.5 text-xl font-bold text-white">
              See a complete solution in under a minute
            </h2>
            <p className="mt-1.5 max-w-lg text-sm text-slate-300">
              Load a worked example, press solve, then explore the steps, table, graph and
              theory — no setup required.
            </p>
          </div>
          <Link
            to={`/methods/${STARTER_METHOD.id}`}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-indigo-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          >
            Open {STARTER_METHOD.name.replace(/ Method$/, "")}
            <Icon name="arrowRight" size={15} />
          </Link>
        </div>
      </section>
    </div>
  );
}

function CatalogueStats() {
  const chapters = useCatalogStore((state) => state.chapters);
  const status = useCatalogStore((state) => state.status);
  const ready = status === "ready";
  const available = chapters.reduce((sum, chapter) => sum + chapter.available_count, 0);
  const total = chapters.reduce((sum, chapter) => sum + chapter.method_count, 0);

  return (
    <dl className="mt-8 grid max-w-md grid-cols-3 gap-3">
      {[
        { value: ready ? `${available}/${total}` : "—", label: "Methods ready" },
        { value: ready ? String(chapters.length) : "—", label: "Chapters" },
        { value: "PDF + CSV", label: "Report exports" },
      ].map((stat) => (
        <div
          key={stat.label}
          className="rounded-xl border border-slate-200/70 bg-white/60 px-3 py-2.5 backdrop-blur dark:border-white/[0.07] dark:bg-white/[0.03]"
        >
          <dt className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
            {stat.label}
          </dt>
          <dd className="mt-0.5 text-sm font-bold text-slate-800 dark:text-slate-100">
            {stat.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ChapterCatalogue() {
  const chapters = useCatalogStore((state) => state.chapters);
  const status = useCatalogStore((state) => state.status);
  const error = useCatalogStore((state) => state.error);
  const load = useCatalogStore((state) => state.load);
  const loading = status === "loading" || status === "idle";
  const total = chapters.reduce((sum, chapter) => sum + chapter.method_count, 0);

  return (
    <section id="chapters" className="scroll-mt-24">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className={ui.sectionLabel}>Syllabus</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Browse by chapter
          </h2>
        </div>
        {!loading && (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {total} methods across {chapters.length} chapters
          </p>
        )}
      </div>

      {status === "error" && error && (
        <ErrorState
          title="The syllabus could not load"
          error={error}
          onRetry={() => void load(true)}
          retryLabel="Reload catalogue"
          className="mb-4"
        />
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className={`min-h-[13.5rem] p-5 ${ui.card}`}>
              <LoadingSkeleton lines={3} />
            </div>
          ))}
        </div>
      ) : chapters.length === 0 ? (
        status === "error" ? null : (
          <EmptyState
            icon="layers"
            title="No chapters yet"
            description="The syllabus catalogue is empty. Reload it to pull the latest chapter list."
            action={
              <button type="button" onClick={() => void load(true)} className={ui.btn}>
                <Icon name="refresh" size={14} />
                Reload catalogue
              </button>
            }
          />
        )
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {chapters.map((chapter) => {
            const visual = chapterVisual(chapter.id);
            const percent =
              chapter.method_count === 0
                ? 0
                : Math.round((chapter.available_count / chapter.method_count) * 100);
            return (
              <Link
                key={chapter.id}
                to={`/chapters/${chapter.id}`}
                className={`group relative flex min-h-[13.5rem] flex-col overflow-hidden p-5 ${ui.card} ${ui.cardHover}`}
              >
                <div className="flex items-start justify-between">
                  <span
                    className={`flex h-11 w-11 items-center justify-center rounded-2xl ${visual.tint}`}
                  >
                    <Icon name={visual.icon} size={21} />
                  </span>
                  <span className="font-mono text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                    {String(chapter.number).padStart(2, "0")}
                  </span>
                </div>

                <h3 className="mt-4 text-[15px] font-semibold text-slate-900 dark:text-slate-100">
                  {chapter.title}
                </h3>
                <p className="mt-1.5 flex-1 text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">
                  {chapter.description}
                </p>

                <div className="mt-4 flex items-center justify-between text-[11px]">
                  <span className="font-medium text-slate-500 dark:text-slate-400">
                    {chapter.available_count} of {chapter.method_count} available
                  </span>
                  <span className="inline-flex items-center gap-1 font-semibold text-slate-600 transition group-hover:text-indigo-600 dark:text-slate-300 dark:group-hover:text-indigo-300">
                    Open
                    <Icon
                      name="arrowRight"
                      size={13}
                      className="transition group-hover:translate-x-0.5"
                    />
                  </span>
                </div>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-100 dark:bg-white/[0.06]">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${visual.gradient}`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}

/** Decorative sample result card for the hero (static, not connected to the API). */
function SamplePreview() {
  return (
    <div className="relative hidden animate-fade-up sm:block stagger-2">
      <div
        aria-hidden="true"
        className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-indigo-500/10 via-violet-500/10 to-teal-400/10 blur-2xl"
      />
      <div className="relative rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-2xl shadow-slate-900/10 backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/80 dark:shadow-black/30">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">
            <Icon name="sparkles" size={13} />
            Live preview
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Converged
          </span>
        </div>

        <div className="mt-4 rounded-xl border border-slate-200/70 bg-slate-50/70 px-3.5 py-3 dark:border-white/[0.06] dark:bg-slate-950/40">
          <p className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
            Solve for the root of
          </p>
          <p className="mt-1 font-mono text-sm text-slate-700 dark:text-slate-200">
            f(x) = x³ − x − 1
          </p>
        </div>

        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Approximate root
            </p>
            <p className="mt-0.5 font-mono text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
              1.324718
            </p>
          </div>
          <span className="rounded-lg bg-indigo-50 px-2 py-1 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">
            20 iterations
          </span>
        </div>

        <svg
          viewBox="0 0 280 104"
          className="mt-4 h-24 w-full text-indigo-500 dark:text-indigo-400"
          role="img"
          aria-label="Illustrative curve crossing the x-axis at the root"
        >
          <defs>
            <linearGradient id="hero-curve" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.35" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
          </defs>
          <g stroke="currentColor" strokeOpacity="0.12" strokeWidth="1">
            <path d="M0 78h280" />
            <path d="M0 26h280" />
            <path d="M188 0v104" />
          </g>
          <path
            d="M8 96C42 92 56 82 74 64s20-44 38-46 26 24 38 40 24 18 58 10"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
          <path
            d="M8 96C42 92 56 82 74 64s20-44 38-46 26 24 38 40 24 18 58 10v36H8Z"
            fill="url(#hero-curve)"
          />
          <g>
            <line
              x1="188"
              y1="18"
              x2="188"
              y2="86"
              stroke="currentColor"
              strokeDasharray="3 4"
              strokeOpacity="0.5"
            />
            <circle cx="188" cy="66" r="4.5" fill="currentColor" />
            <circle cx="188" cy="66" r="9" fill="currentColor" fillOpacity="0.14" />
          </g>
        </svg>

        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-[11px] dark:border-white/[0.06]">
          <span className="text-slate-600 dark:text-slate-400">Absolute error</span>
          <span className="font-mono font-medium text-slate-700 dark:text-slate-200">
            9.5 × 10⁻⁷
          </span>
        </div>
      </div>

      <div className="absolute -bottom-4 -left-4 flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white/95 px-3 py-2 text-[11px] font-medium text-slate-600 shadow-lg backdrop-blur dark:border-white/10 dark:bg-slate-900/95 dark:text-slate-300">
        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
          <Icon name="list" size={13} />
        </span>
        Step-by-step working
      </div>
    </div>
  );
}
