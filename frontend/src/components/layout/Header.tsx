import { Link } from "react-router-dom";

import { SearchBar } from "./SearchBar";
import { ThemeToggle } from "./ThemeToggle";
import { BrandMark } from "../ui/BrandMark";
import { Icon } from "../ui/Icon";

/** Top bar: brand, global search, shortcut help, theme switch and menu toggle. */
export function Header({
  onToggleSidebar,
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
    <header className="site-header no-print sticky top-0 z-40 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <div className="mx-auto flex h-16 max-w-[1680px] items-center gap-0 px-0">
        <div className="flex h-16 w-[56px] shrink-0 items-center justify-center">
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label="Toggle sidebar"
            aria-keyshortcuts="Ctrl+B Meta+B"
            title="Toggle sidebar (Ctrl+B / ⌘B)"
            className="flex h-10 w-10 items-center justify-center rounded-xl text-[color:var(--color-ink-muted)] transition hover:bg-[color:var(--color-surface-2)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] lg:inline hidden sm:flex"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 7h16" />
              <path d="M4 12h16" />
              <path d="M4 17h16" />
            </svg>
            <span className="sr-only">Toggle sidebar (Ctrl+B / ⌘B)</span>
          </button>
        </div>

        <Link
          to="/"
          aria-label="Numerical Methods Solver — home"
          className="group ml-3 flex min-w-0 shrink-0 items-center gap-2"
        >
          <BrandMark className="h-8 w-8 shrink-0 transition" />
          <span className="hidden max-w-[200px] truncate text-sm font-semibold tracking-tight text-[color:var(--color-ink)] sm:block">
            Numerical Methods Solver
          </span>
        </Link>
        <span
          className="ml-2 hidden shrink-0 items-center rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-2 py-1 font-mono text-[10px] font-medium text-[color:var(--color-ink-muted)] md:inline-flex"
          title="ENSH 252 · IOE / Tribhuvan University"
        >
          ENSH 252
        </span>

        <div className="flex min-w-0 flex-1 justify-center px-1">
          <SearchBar />
        </div>

        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          <button
            type="button"
            onClick={onOpenShortcuts}
            aria-label="Keyboard shortcuts"
            aria-keyshortcuts="?"
            title="Keyboard shortcuts (?)"
            className="inline-flex items-center gap-1.5 rounded-xl px-2.5 py-2 text-sm font-medium text-[color:var(--color-ink-muted)] transition hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-ink)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]"
          >
            <Icon name="keyboard" size={16} />
            <kbd className="hidden rounded border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-1 font-mono text-[10px] text-[color:var(--color-ink-muted)] lg:inline">
              ?
            </kbd>
          </button>
          <button
            type="button"
            onClick={onToggleFocus}
            aria-pressed={focusMode}
            aria-label={focusMode ? "Exit focus" : "Focus"}
            title={focusMode ? "Exit focus mode (F)" : "Focus mode (F)"}
            className={`inline-flex items-center gap-1.5 rounded-xl px-2.5 py-2 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] ${
              focusMode
                ? "text-[color:var(--color-accent)] bg-[color:var(--color-accent-soft)]"
                : "text-[color:var(--color-ink-muted)] hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-ink)]"
            }`}
          >
            <Icon name={focusMode ? "arrowUpRight" : "panelLeft"} size={16} />
            <span className="hidden sm:inline">{focusMode ? "Exit focus" : "Focus"}</span>
          </button>
          <Link
            to="/about"
            className="rounded-xl px-3 py-2 text-sm font-medium text-[color:var(--color-ink-muted)] transition hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-ink)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]"
          >
            About
          </Link>
        </nav>

        <ThemeToggle />
      </div>
    </header>
  );
}
