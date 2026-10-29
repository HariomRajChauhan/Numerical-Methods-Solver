import { Suspense, useCallback, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { useCatalog } from "../../hooks/useCatalog";
import { Toaster } from "../Toaster";
import { LoadingSkeleton } from "../LoadingSkeleton";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { ShortcutsSheet } from "./ShortcutsSheet";
import { Sidebar } from "./Sidebar";
import { useSidebarStore } from "../../store/sidebar";

/**
 * App shell: header + sidebar (desktop) / drawer (mobile) + routed content.
 * Only renders chrome — every page lives in an <Outlet />.
 *
 * Sidebar keyboard shortcuts (Ctrl+B cycle, F focus mode) are handled
 * directly inside Sidebar so the component works standalone.
 */
export function AppLayout() {
  useCatalog();
  const location = useLocation();

  const cycle = useSidebarStore((state) => state.cycle);
  const focusMode = useSidebarStore((state) => state.focusMode);
  const setFocusMode = useSidebarStore((state) => state.setFocusMode);

  // Drawer state is tied to the route it was opened on, so navigating closes it
  // without a synchronising effect.
  const [openFor, setOpenFor] = useState<string | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const drawerOpen = openFor === location.pathname;
  const closeShortcuts = useCallback(() => setShortcutsOpen(false), []);

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

  useEffect(() => {
    function handleShortcutSheet(event: KeyboardEvent): void {
      if (
        (event.key !== "?" && !(event.key === "/" && event.shiftKey)) ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.defaultPrevented
      ) {
        return;
      }
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if (typing) return;
      event.preventDefault();
      setShortcutsOpen(true);
    }
    window.addEventListener("keydown", handleShortcutSheet);
    return () => window.removeEventListener("keydown", handleShortcutSheet);
  }, []);

  return (
    <div
      id="top"
      className="app-shell min-h-dvh bg-slate-50 dark:bg-[#070a13]"
      data-focus={focusMode}
    >
      <a
        href="#main-content"
        className={`sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-indigo-600 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:shadow-lg ${
          focusMode ? "hidden" : ""
        }`}
      >
        Skip to content
      </a>

      {!focusMode && (
        <Header
          onToggleSidebar={cycle}
          sidebarOpen={drawerOpen}
          onOpenShortcuts={() => setShortcutsOpen(true)}
          onToggleFocus={() => setFocusMode(!focusMode)}
          focusMode={focusMode}
        />
      )}

      {!focusMode ? (
        <div className="mx-auto flex w-full max-w-[1680px]">
          {/* Desktop sidebar — three states (managed internally by Sidebar) */}
          <Sidebar onNavigate={() => setDrawer(false)} />

          {drawerOpen && (
            <>
              <div
                role="presentation"
                onClick={() => setDrawer(false)}
                className="no-print fixed inset-x-0 bottom-0 top-16 z-30 bg-slate-950/40 backdrop-blur-sm lg:hidden"
              />
              <aside
                aria-label="Navigation"
                className="site-sidebar no-print fixed bottom-0 left-0 top-16 z-40 w-[19rem] max-w-[86vw] animate-slide-in overflow-y-auto border-r border-slate-200/80 bg-white shadow-2xl scroll-slim lg:hidden dark:border-white/10 dark:bg-[#0b1020]"
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
            <Suspense
              fallback={
                <div className="mx-auto min-h-[calc(100dvh-4rem)] max-w-6xl space-y-5 py-2">
                  <LoadingSkeleton lines={2} />
                  <LoadingSkeleton lines={6} />
                </div>
              }
            >
              <Outlet />
            </Suspense>
          </main>
        </div>
      ) : (
        // Focus mode: full viewport workspace, no header or sidebar.
        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-dvh w-full px-4 py-6 focus:outline-none sm:px-6 lg:px-8 lg:py-8"
        >
          <Suspense
            fallback={
              <div className="mx-auto min-h-dvh max-w-6xl space-y-5 py-2">
                <LoadingSkeleton lines={2} />
                <LoadingSkeleton lines={6} />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>
      )}

      {!focusMode && <Footer onOpenShortcuts={() => setShortcutsOpen(true)} />}

      <ShortcutsSheet open={shortcutsOpen} onClose={closeShortcuts} />
      <Toaster />
    </div>
  );
}
