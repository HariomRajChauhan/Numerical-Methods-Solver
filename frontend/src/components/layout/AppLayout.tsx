import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { useCatalog } from "../../hooks/useCatalog";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

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

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Header onToggleSidebar={() => setDrawer(!drawerOpen)} sidebarOpen={drawerOpen} />
      <div className="mx-auto flex w-full max-w-[1600px]">
        <aside className="sticky top-[57px] hidden h-[calc(100vh-57px)] w-72 shrink-0 overflow-y-auto border-r border-slate-200 lg:block dark:border-slate-800">
          <Sidebar />
        </aside>

        {drawerOpen && (
          <>
            <div
              role="presentation"
              onClick={() => setDrawer(false)}
              className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
            />
            <aside
              aria-label="Navigation"
              className="fixed left-0 top-[57px] z-40 h-[calc(100vh-57px)] w-72 overflow-y-auto border-r border-slate-200 bg-white lg:hidden dark:border-slate-800 dark:bg-slate-900"
            >
              <Sidebar onNavigate={() => setDrawer(false)} />
            </aside>
          </>
        )}

        <main className="min-w-0 flex-1 px-3 py-5 sm:px-5 lg:px-6">
          <Outlet />
        </main>
      </div>
      <footer className="border-t border-slate-200 px-4 py-6 text-center text-xs text-slate-500 dark:border-slate-800">
        <Link to="/about" className="hover:text-indigo-600 dark:hover:text-indigo-400">
          About
        </Link>
        <span aria-hidden="true"> · </span>
        Numerical Methods · ENSH 252 · IOE / Tribhuvan University
      </footer>
    </div>
  );
}
