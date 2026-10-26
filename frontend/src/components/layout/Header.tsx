import { Link } from "react-router-dom";

import { SearchBar } from "./SearchBar";
import { ThemeToggle } from "./ThemeToggle";
import { Icon } from "../ui/Icon";

/** Top bar: brand, global search, theme switch and the mobile drawer toggle. */
export function Header({
  onToggleSidebar,
  sidebarOpen,
}: {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl dark:border-white/[0.06] dark:bg-[#070a13]/80">
      <div className="mx-auto flex h-16 max-w-[1680px] items-center gap-2 px-3 sm:gap-3 sm:px-5">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={sidebarOpen}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 lg:hidden dark:border-white/10 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Icon name={sidebarOpen ? "close" : "menu"} size={18} />
          </button>
        )}

        <Link
          to="/"
          aria-label="Numerical Methods Solver — home"
          className="group flex shrink-0 items-center gap-2.5"
        >
          <span className="relative inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30 transition group-hover:shadow-indigo-500/40">
            <Icon name="sigma" size={19} strokeWidth={2.1} />
          </span>
          <span className="hidden truncate text-sm font-semibold tracking-tight text-slate-900 sm:block dark:text-white">
            Numerical Methods Solver
          </span>
        </Link>

        <span
          className="hidden shrink-0 items-center rounded-lg border border-slate-200/80 bg-slate-50/80 px-2 py-1 font-mono text-[10px] font-medium text-slate-600 xl:inline-flex dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-400"
          title="ENSH 252 · IOE / Tribhuvan University"
        >
          ENSH 252
        </span>

        <div className="flex min-w-0 flex-1 justify-center px-1">
          <SearchBar />
        </div>

        <nav aria-label="Primary" className="hidden items-center md:flex">
          <Link
            to="/about"
            className="rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-white"
          >
            About
          </Link>
        </nav>

        <ThemeToggle />
      </div>
    </header>
  );
}
