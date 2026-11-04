import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { useCatalog } from "../../hooks/useCatalog";
import { Toaster } from "../Toaster";
import { LoadingSkeleton } from "../LoadingSkeleton";
import { Icon } from "../ui/Icon";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { ShortcutsSheet } from "./ShortcutsSheet";
import { Sidebar } from "./Sidebar";
import { useSidebarStore } from "../../store/sidebar";
import { ui } from "../../utils/ui";

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
  const drawerRef = useRef<HTMLDivElement>(null);
  const drawerCloseRef = useRef<HTMLButtonElement>(null);

  function setDrawer(open: boolean): void {
    setOpenFor(open ? location.pathname : null);
  }

  /**
   * Below `lg` the menu button opens the navigation drawer; from `lg` up it
   * keeps its original behaviour of cycling the desktop sidebar state.
   */
  function handleToggleSidebar(): void {
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches) {
      setDrawer(!drawerOpen);
      return;
    }
    cycle();
  }

  useEffect(() => {
    function handleFocusKeys(event: KeyboardEvent) {
      if (!focusMode) return;
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if (typing) return;
      if (event.key.toLowerCase() === "f" || event.key === "Escape") {
        event.preventDefault();
        setFocusMode(false);
      }
    }
    document.addEventListener("keydown", handleFocusKeys);
    return () => document.removeEventListener("keydown", handleFocusKeys);
  }, [focusMode, setFocusMode]);

  // Mobile drawer: lock scroll, move focus inside, trap Tab and restore focus
  // to the trigger when the drawer closes (Escape, backdrop, close or route).
  useEffect(() => {
    if (!drawerOpen) return;

    const trigger = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const frame = window.requestAnimationFrame(() => drawerCloseRef.current?.focus());

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpenFor(null);
        return;
      }
      if (event.key !== "Tab") return;

      const root = drawerRef.current;
      if (!root) return;
      const focusable = Array.from(
        root.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter((element) => element.offsetParent !== null);
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.cancelAnimationFrame(frame);
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      trigger?.focus?.();
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
      className="min-h-dvh bg-[color:var(--color-canvas)]"
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
          onToggleSidebar={handleToggleSidebar}
          sidebarOpen={drawerOpen}
          onOpenShortcuts={() => setShortcutsOpen(true)}
          onToggleFocus={() => setFocusMode(!focusMode)}
          focusMode={focusMode}
        />
      )}

      {!focusMode ? (
        <div className="mx-auto flex w-full max-w-[1680px]">
          {/* Desktop sidebar — three states (managed internally by Sidebar) */}
          <Sidebar
            className="hidden lg:block"
            onNavigate={() => setDrawer(false)}
          />

          {drawerOpen && (
            <>
              <div
                role="presentation"
                onClick={() => setDrawer(false)}
                className="no-print fixed inset-x-0 bottom-0 top-16 z-30 bg-slate-950/40 backdrop-blur-sm lg:hidden"
              />
              <div
                ref={drawerRef}
                id="mobile-navigation"
                role="dialog"
                aria-modal="true"
                aria-label="Navigation menu"
                className="no-print fixed bottom-0 left-0 top-16 z-40 flex w-[19rem] max-w-[86vw] flex-col overflow-hidden border-r border-[color:var(--color-border)] bg-[color:var(--color-surface)] shadow-2xl animate-slide-in lg:hidden"
              >
                <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[color:var(--color-border)] px-4 py-3">
                  <div className="min-w-0">
                    <p className={ui.sectionLabel}>Navigation</p>
                    <p className="truncate text-sm font-semibold text-[color:var(--color-ink)]">
                      Numerical Methods Solver
                    </p>
                  </div>
                  <button
                    ref={drawerCloseRef}
                    type="button"
                    onClick={() => setDrawer(false)}
                    aria-label="Close navigation menu"
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control text-[color:var(--color-ink-muted)] transition hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-ink)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]"
                  >
                    <Icon name="close" size={18} />
                  </button>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto scroll-slim">
                  <Sidebar
                    variant="drawer"
                    onNavigate={() => setDrawer(false)}
                  />
                </div>
              </div>
            </>
          )}

          <main
            id="main-content"
            tabIndex={-1}
            className="min-w-0 flex-1 px-4 py-6 focus:outline-none sm:px-6 lg:px-8 lg:py-8"
          >
            <Suspense
              fallback={
                <div className="mx-auto min-h-[calc(100dvh-4rem)] w-full max-w-[1760px] space-y-5 px-6 py-2">
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
          <button
            type="button"
            onClick={() => setFocusMode(false)}
            aria-label="Exit focus mode"
            className="fixed right-4 top-4 z-[100] rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-xl ring-2 ring-indigo-500 transition hover:bg-slate-50 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700"
          >
            Exit focus (F or Esc)
          </button>
          <Suspense
            fallback={
              <div className="mx-auto min-h-dvh w-full max-w-[1760px] space-y-5 px-6 py-2">
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
