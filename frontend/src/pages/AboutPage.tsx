import { Link } from "react-router-dom";

import { ui } from "../utils/ui";

export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-xl font-bold text-slate-900 dark:text-slate-50">About</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          An all-in-one solver for the numerical methods practicals of ENSH 252 (IOE / Tribhuvan
          University). Every method returns the final answer, exam-style step-by-step working,
          iteration tables, an interactive graph, error and convergence information, and a
          downloadable report.
        </p>
      </header>

      <section className={`p-5 text-sm ${ui.card}`}>
        <h2 className="font-semibold text-slate-800 dark:text-slate-200">How it works</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-600 dark:text-slate-400">
          <li>All numerical work happens in the Python backend (NumPy / SciPy / SymPy).</li>
          <li>
            The input forms are generated from each method's schema, so new methods appear
            automatically without UI changes.
          </li>
          <li>Plain-text formulas are parsed safely — no code is ever executed from your input.</li>
        </ul>
      </section>

      <section className={`p-5 text-sm ${ui.card}`}>
        <h2 className="font-semibold text-slate-800 dark:text-slate-200">Chapters</h2>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Non-linear equations · Linear systems · Interpolation · Differentiation &amp; integration ·
          ODEs · PDEs
        </p>
      </section>

      <Link to="/" className={ui.btnPrimary}>
        Back to home
      </Link>
    </div>
  );
}
