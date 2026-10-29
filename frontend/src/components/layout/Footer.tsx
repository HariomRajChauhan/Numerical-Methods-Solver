import { Link } from "react-router-dom";

import { useCatalogStore } from "../../store/catalog";
import { BrandMark } from "../ui/BrandMark";
import { Icon } from "../ui/Icon";

interface FooterProps {
  onOpenShortcuts: () => void;
}

const PRODUCT_LINKS = [
  { to: "/#chapters", label: "Browse syllabus" },
  { to: "/methods/newton_raphson", label: "Try a popular method" },
  { to: "/about", label: "About the project" },
];

/** Site footer: brand, syllabus shortcuts, source link and keyboard help. */
export function Footer({ onOpenShortcuts }: FooterProps) {
  const chapters = useCatalogStore((state) => state.chapters);
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer no-print border-t border-line bg-surface/55 backdrop-blur-sm">
      <div className="mx-auto max-w-[1680px] px-5 py-9 sm:px-6 lg:px-8">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-[1.55fr_1fr_1fr_1.15fr]">
          <div className="max-w-sm">
            <Link
              to="/"
              aria-label="Numerical Methods Solver — home"
              className="inline-flex items-center gap-2.5"
            >
              <BrandMark className="h-8 w-8" iconSize={16} />
              <span className="text-sm font-semibold tracking-tight text-ink">
                Numerical Methods Solver
              </span>
            </Link>
            <p className="mt-3 text-xs leading-relaxed text-ink-muted">
              Exam-ready numerical methods for ENSH 252. Every answer comes with the working,
              iteration table, graph and downloadable report.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <a
                href="https://github.com/HariomRajChauhan/Numerical-Methods-Solver"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-control border border-line bg-surface px-2.5 py-1.5 text-2xs font-medium text-ink-muted transition hover:border-accent-soft-line hover:text-accent-text"
              >
                <Icon name="external" size={13} />
                View source
              </a>
              <span className="inline-flex items-center gap-1.5 rounded-control bg-surface-muted px-2.5 py-1.5 text-2xs font-medium text-ink-muted">
                <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-success" />
                No account needed
              </span>
            </div>
          </div>

          <nav aria-label="Product">
            <h2 className="text-2xs font-semibold uppercase tracking-[0.16em] text-ink-muted">
              Product
            </h2>
            <ul className="mt-3 space-y-2">
              {PRODUCT_LINKS.map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.to}
                    className="text-xs text-ink-muted transition hover:text-accent-text"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  onClick={onOpenShortcuts}
                  className="inline-flex items-center gap-1.5 text-xs text-ink-muted transition hover:text-accent-text"
                >
                  Keyboard shortcuts
                  <kbd className="rounded border border-line bg-surface-muted px-1 font-mono text-[10px]">
                    ?
                  </kbd>
                </button>
              </li>
            </ul>
          </nav>

          <nav aria-label="Syllabus">
            <h2 className="text-2xs font-semibold uppercase tracking-[0.16em] text-ink-muted">
              Syllabus
            </h2>
            <ul className="mt-3 min-h-44 space-y-2">
              {chapters.length > 0 ? (
                chapters.map((chapter) => (
                  <li key={chapter.id}>
                    <Link
                      to={`/chapters/${chapter.id}`}
                      className="text-xs text-ink-muted transition hover:text-accent-text"
                    >
                      {chapter.title}
                    </Link>
                  </li>
                ))
              ) : (
                <li className="text-xs text-ink-subtle">Six chapters · 30+ methods</li>
              )}
            </ul>
          </nav>

          <div>
            <h2 className="text-2xs font-semibold uppercase tracking-[0.16em] text-ink-muted">
              Built for
            </h2>
            <p className="mt-3 text-xs leading-relaxed text-ink-muted">
              ENSH 252 · IOE / Tribhuvan University. Use the results as a revision aid and always
              check the method&apos;s assumptions before quoting an answer.
            </p>
            <Link
              to="/about"
              className="mt-3 inline-flex items-center gap-1 text-2xs font-semibold text-accent-text transition hover:opacity-75"
            >
              How it works
              <Icon name="arrowRight" size={12} />
            </Link>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-2 border-t border-line pt-4 text-2xs text-ink-subtle sm:flex-row sm:items-center sm:justify-between">
          <p>© {year} Numerical Methods Solver. Built as a study companion.</p>
          <p className="inline-flex items-center gap-1.5">
            <Icon name="shield" size={12} />
            Client-safe inputs · server-verified results
          </p>
        </div>
      </div>
    </footer>
  );
}
