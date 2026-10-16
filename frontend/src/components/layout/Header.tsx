import { Link } from "react-router-dom";

import { SearchBar } from "./SearchBar";
import { ThemeToggle } from "./ThemeToggle";

/** Top bar: brand, search, theme switch and the mobile sidebar toggle. */
export function Header({
  onToggleSidebar,
  sidebarOpen,
}: {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
      <div className="flex items-center gap-3 px-3 py-2.5 sm:px-4">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={sidebarOpen}
            className="rounded-lg border border-slate-300 p-2 text-slate-600 lg:hidden dark:border-slate-700 dark:text-slate-300"
          >
            ☰
          </button>
        )}
        <Link to="/" className="flex shrink-0 items-center gap-2">
          <span
            aria-hidden="true"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white"
          >
            ∑
          </span>
          <span className="hidden text-sm font-semibold sm:inline">
            Numerical Methods Solver
          </span>
        </Link>
        <div className="flex flex-1 justify-center">
          <SearchBar />
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
