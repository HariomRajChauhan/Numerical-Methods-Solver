import { Link } from "react-router-dom";

import { Icon, type IconName } from "../components/ui/Icon";
import { usePageTitle } from "../hooks/usePageTitle";
import { useCatalogStore } from "../store/catalog";
import { chapterVisual } from "../utils/chapters";
import { ui } from "../utils/ui";

const PRINCIPLES: { icon: IconName; title: string; text: string }[] = [
  {
    icon: "sparkles",
    title: "Everything in one place",
    text: "Final answer, exam-style steps, iteration tables, graphs, convergence data, theory and code — without switching between tools.",
  },
  {
    icon: "bookOpen",
    title: "No black boxes",
    text: "Each method explains itself: the formula behind it, the algorithm in pseudocode and the exact Python source that ran your problem.",
  },
  {
    icon: "shield",
    title: "Safe, checked input",
    text: "Expressions are parsed with a whitelist and validated on the server. Nothing you type is ever executed, and errors are written in plain language.",
  },
  {
    icon: "monitor",
    title: "Made for any screen",
    text: "A focused desktop workspace for long derivations, and a comfortable single-column layout on phones and tablets.",
  },
];

const STACK = [
  "React 19",
  "TypeScript",
  "Vite",
  "Tailwind CSS",
  "Plotly",
  "KaTeX",
  "FastAPI",
  "NumPy",
  "SciPy",
  "SymPy",
  "Python 3.11+",
];

export function AboutPage() {
  usePageTitle("About");
  const chapters = useCatalogStore((state) => state.chapters);

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-xl shadow-slate-900/[0.04] sm:p-9 dark:border-white/[0.07] dark:bg-slate-900/40 dark:shadow-none">
        <div aria-hidden="true" className="bg-grid absolute inset-0 opacity-70" />
        <div
          aria-hidden="true"
          className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-indigo-500/15 blur-3xl"
        />
        <div className="relative">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200/80 bg-white/80 px-3 py-1.5 text-[11px] font-semibold text-indigo-700 shadow-sm backdrop-blur dark:border-indigo-400/20 dark:bg-indigo-500/10 dark:text-indigo-200">
            <Icon name="cap" size={13} />
            ENSH 252 · IOE / Tribhuvan University
          </span>
          <h1 className="mt-5 max-w-2xl text-balance text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl dark:text-white">
            A study companion for numerical methods.
          </h1>
          <p className="mt-3 max-w-2xl text-pretty text-sm leading-relaxed text-slate-600 sm:text-base dark:text-slate-300">
            This platform solves the numerical-methods practicals of ENSH 252 and shows the work
            behind every answer: exam-style steps, iteration tables, an interactive graph, error
            and convergence information, and a downloadable report.
          </p>
          <div className="mt-6 flex flex-wrap gap-2.5">
            <Link to="/" className={ui.btnPrimary}>
              <Icon name="bookOpen" size={16} />
              Browse chapters
            </Link>
            <Link to="/methods/bisection" className={ui.btn}>
              <Icon name="play" size={14} />
              Try a worked example
            </Link>
          </div>
        </div>
      </header>

      <section aria-labelledby="principles-heading">
        <p className={ui.sectionLabel}>Design principles</p>
        <h2
          id="principles-heading"
          className="mt-1 text-xl font-bold tracking-tight text-slate-900 dark:text-white"
        >
          Built around how students actually revise
        </h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {PRINCIPLES.map((principle) => (
            <div key={principle.title} className={`p-5 ${ui.card}`}>
              <span className={`${ui.iconBox} h-10 w-10`}>
                <Icon name={principle.icon} size={18} />
              </span>
              <h3 className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-100">
                {principle.title}
              </h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {principle.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className={`p-5 sm:p-6 ${ui.card}`} aria-labelledby="syllabus-heading">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className={ui.sectionLabel}>Coverage</p>
            <h2
              id="syllabus-heading"
              className="mt-1 text-xl font-bold tracking-tight text-slate-900 dark:text-white"
            >
              The six syllabus chapters
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            New methods appear automatically as they are added.
          </p>
        </div>

        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {chapters.map((chapter) => {
            const visual = chapterVisual(chapter.id);
            return (
              <li key={chapter.id}>
                <Link
                  to={`/chapters/${chapter.id}`}
                  className="group flex items-center gap-3 rounded-xl border border-slate-200/70 px-3 py-2.5 transition hover:border-indigo-300/70 hover:bg-slate-50/60 dark:border-white/[0.06] dark:hover:border-indigo-400/30 dark:hover:bg-white/[0.03]"
                >
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${visual.tint}`}
                  >
                    <Icon name={visual.icon} size={15} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                      {chapter.title}
                    </span>
                    <span className="block text-[11px] text-slate-600 dark:text-slate-400">
                      {chapter.available_count} of {chapter.method_count} available
                    </span>
                  </span>
                  <Icon
                    name="arrowRight"
                    size={14}
                    className="shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-indigo-500 dark:text-slate-600"
                  />
                </Link>
              </li>
            );
          })}
          {chapters.length === 0 && (
            <li className="text-sm text-slate-500 dark:text-slate-400">
              Non-linear equations, linear systems, interpolation, differentiation and integration,
              ODEs and PDEs.
            </li>
          )}
        </ul>
      </section>

      <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
        <section className={`p-5 sm:p-6 ${ui.card}`} aria-labelledby="stack-heading">
          <p className={ui.sectionLabel}>Under the hood</p>
          <h2
            id="stack-heading"
            className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white"
          >
            A simple, open stack
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
            A React front end talks to a Python backend that does the actual numerical work. The
            input forms are generated from each method&apos;s schema, so the interface stays
            consistent as the catalogue grows.
          </p>
          <ul className="mt-4 flex flex-wrap gap-1.5">
            {STACK.map((item) => (
              <li key={item}>
                <span className="inline-flex rounded-lg border border-slate-200/80 bg-slate-50 px-2.5 py-1 font-mono text-[11px] text-slate-600 dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-slate-300">
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className={`p-5 sm:p-6 ${ui.card}`} aria-labelledby="notes-heading">
          <p className={ui.sectionLabel}>Good to know</p>
          <h2
            id="notes-heading"
            className="mt-1 text-lg font-bold tracking-tight text-slate-900 dark:text-white"
          >
            For your lab file
          </h2>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            <li className="flex gap-2">
              <Icon name="check" size={14} className="mt-0.5 shrink-0 text-emerald-500" />
              Always cross-check the method&apos;s assumptions before quoting a result.
            </li>
            <li className="flex gap-2">
              <Icon name="check" size={14} className="mt-0.5 shrink-0 text-emerald-500" />
              Report downloads re-run the solver, so the numbers always match the screen.
            </li>
            <li className="flex gap-2">
              <Icon name="check" size={14} className="mt-0.5 shrink-0 text-emerald-500" />
              Coming-soon chapters already include readable theory and pseudocode for revision.
            </li>
          </ul>
        </section>
      </div>

      <section className="flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white/60 p-5 sm:flex-row sm:items-center sm:justify-between dark:border-white/[0.07] dark:bg-white/[0.02]">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Ready to see a full solution? Start with the bisection method — it needs nothing more
          than a function and an interval.
        </p>
        <Link to="/methods/bisection" className={`${ui.btnPrimary} shrink-0`}>
          Open Bisection
          <Icon name="arrowRight" size={15} />
        </Link>
      </section>
    </div>
  );
}
