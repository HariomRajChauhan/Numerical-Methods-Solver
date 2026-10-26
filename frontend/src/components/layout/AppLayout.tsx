import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { useCatalog } from "../../hooks/useCatalog";
import { Toaster } from "../Toaster";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { Icon } from "../ui/Icon";

/**
 * App shell: header + persistent sidebar (drawer on mobile) + routed content.
 * Only renders chrome — every page lives in an <Outlet />.
 */
export function AppLayout() {
  useCatalog();
  const location = useLocation();
  // Drawer state is tied to the route it was opened on, so navigating closes it
  // without a synchronising effect.
  const [openFor, setOpenFor] = useState<string | null>(null);
  const drawerOpen = openFor === location.pathname;

  function setDrawer(open: boolean): void {
    setOpenFor(open ? location.pathname : null);
  }

  useEffect(() => {
    if (!drawerOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function handleEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") setOpenFor(null);
    }
    window.addEventListener("keydown", handleEscape);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", handleEscape);
    };
  }, [drawerOpen]);

  return (
    <div id="top" className="app-shell min-h-dvh bg-slate-50 dark:bg-[#070a13]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-indigo-600 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:shadow-lg"
      >
        Skip to content
      </a>

      <Header onToggleSidebar={() => setDrawer(!drawerOpen)} sidebarOpen={drawerOpen} />

      <div className="mx-auto flex w-full max-w-[1680px]">
        <aside className="sticky top-16 hidden h-[calc(100dvh-4rem)] w-72 shrink-0 overflow-y-auto border-r border-slate-200/70 bg-white/40 scroll-slim backdrop-blur-sm lg:block dark:border-white/[0.06] dark:bg-[#070a13]/30">
          <Sidebar />
        </aside>

        {drawerOpen && (
          <>
            <div
              role="presentation"
              onClick={() => setDrawer(false)}
              className="fixed inset-x-0 bottom-0 top-16 z-30 bg-slate-950/40 backdrop-blur-sm lg:hidden"
            />
            <aside
              aria-label="Navigation"
              className="fixed bottom-0 left-0 top-16 z-40 w-[19rem] max-w-[86vw] animate-slide-in overflow-y-auto border-r border-slate-200/80 bg-white shadow-2xl scroll-slim lg:hidden dark:border-white/10 dark:bg-[#0b1020]"
            >
              <Sidebar onNavigate={() => setDrawer(false)} />
            </aside>
          </>
        )}

        <main
          id="main-content"
          tabIndex={-1}
          className="min-w-0 flex-1 px-4 py-6 focus:outline-none sm:px-6 lg:px-8 lg:py-8"
        >
          <Outlet />
        </main>
      </div>

      <footer className="border-t border-slate-200/80 bg-white/50 backdrop-blur-sm dark:border-white/[0.06] dark:bg-[#070a13]/40">
        <div className="mx-auto flex max-w-[1680px] flex-col gap-4 px-5 py-7 sm:flex-row sm:items-center sm:justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm shadow-indigo-500/30">
              <Icon name="sigma" size={15} />
            </span>
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Numerical Methods Solver
            </span>
          </Link>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Exam-ready solutions for ENSH 252 · IOE / Tribhuvan University
          </p>
          <div className="flex items-center gap-1 text-xs">
            <Link
              to="/"
              className="rounded-lg px-2.5 py-1.5 font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-white"
            >
              Chapters
            </Link>
            <Link
              to="/about"
              className="rounded-lg px-2.5 py-1.5 font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-white"
            >
              About
            </Link>
          </div>
        </div>
      </footer>

      <Toaster />
    </div>
  );
}
