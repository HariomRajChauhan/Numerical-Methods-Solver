import { Link } from "react-router-dom";

import { SearchBar } from "./SearchBar";
import { ThemeToggle } from "./ThemeToggle";
import { BrandMark } from "../ui/BrandMark";
import { Icon } from "../ui/Icon";

/** Top bar: brand, global search, shortcut help, theme switch and menu toggle. */
export function Header({
  onToggleSidebar,
  sidebarOpen,
  onOpenShortcuts,
  onToggleFocus,
  focusMode,
}: {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
  onOpenShortcuts: () => void;
  onToggleFocus: () => void;
  focusMode: boolean;
}) {
  return (
    <header className="site-header no-print sticky top-0 z-40 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl dark:border-white/[0.06] dark:bg-[#070a13]/80">
      <div className="mx-auto flex h-16 max-w-[1680px] items-center gap-2 px-3 sm:gap-3 sm:px-5">
        {/* Desktop sidebar toggle: Ctrl+B / ⌘B */}
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
          aria-keyshortcuts="Ctrl+B Meta+B"
          title="Toggle sidebar (Ctrl+B / ⌘B)"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 lg:inline dark:border-white/10 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 hidden sm:flex"
        >
          <Icon name={sidebarOpen ? "close" : "menu"} size={18} />
          <span className="sr-only">Toggle sidebar (Ctrl+B / ⌘B)</span>
        </button>

        <Link
          to="/"
          aria-label="Numerical Methods Solver — home"
          className="group flex shrink-0 items-center gap-2.5"
        >
          <BrandMark className="h-9 w-9 transition group-hover:shadow-indigo-500/40" />
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
          <button
            type="button"
            onClick={onOpenShortcuts}
            aria-label="Keyboard shortcuts"
            aria-keyshortcuts="?"
            title="Keyboard shortcuts (?)"
            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-white"
          >
            <Icon name="keyboard" size={16} />
            <kbd className="hidden rounded border border-slate-200 bg-slate-50 px-1 font-mono text-[10px] text-slate-500 lg:inline dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-400">
              ?
            </kbd>
          </button>
          <button
            type="button"
            onClick={onToggleFocus}
            aria-pressed={focusMode}
            aria-label={focusMode ? "Exit focus" : "Focus"}
            title={focusMode ? "Exit focus mode (F)" : "Focus mode (F)"}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-white ${
              focusMode
                ? "text-indigo-600 bg-indigo-50 dark:bg-indigo-500/10 dark:text-indigo-300"
                : "text-slate-500 dark:text-slate-400"
            }`}
          >
            <Icon name={focusMode ? "arrowUpRight" : "panelLeft"} size={16} />
            <span className="hidden sm:inline">{focusMode ? "Exit focus" : "Focus"}</span>
          </button>
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
