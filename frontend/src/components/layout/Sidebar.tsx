import { useEffect, useState } from "react";
import { NavLink, useParams } from "react-router-dom";

import { useCatalogStore } from "../../store/catalog";
import { useSidebarStore } from "../../store/sidebar";
import { ui } from "../../utils/ui";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Icon } from "../ui/Icon";
import { SidebarChapter } from "./SidebarChapter";
import { SidebarOpenHandle } from "./SidebarOpenHandle";
import { ThemeToggle } from "./ThemeToggle";

interface SidebarProps {
  /** Called after navigation on mobile (to close the drawer). */
  onNavigate?: () => void;
  /**
   * `drawer` renders the full navigation tree at 100% width for the mobile
   * drawer.
   */
  variant?: "desktop" | "drawer";
  /** Extra classes for the desktop container (e.g. responsive visibility). */
  className?: string;
}

/**
 * Normal expanded sidebar (and mobile drawer). Rail mode has been completely removed.
 */
export function Sidebar({ onNavigate, variant = "desktop", className }: SidebarProps) {
  const { chapterId, methodId } = useParams<{ chapterId?: string; methodId?: string }>();
  const isDrawer = variant === "drawer";

  const mode = useSidebarStore((state) => state.mode);
  const width = useSidebarStore((state) => state.width);
  const recent = useSidebarStore((state) => state.recent);
  const favorites = useSidebarStore((state) => state.favorites);
  const focusMode = useSidebarStore((state) => state.focusMode);
  const setMode = useSidebarStore((state) => state.setMode);
  const cycle = useSidebarStore((state) => state.cycle);
  const addRecent = useSidebarStore((state) => state.addRecent);
  const toggleFavorite = useSidebarStore((state) => state.toggleFavorite);
  const isFavorite = useSidebarStore((state) => state.isFavorite);
  const isRecent = useSidebarStore((state) => state.isRecent);
  const setFocusMode = useSidebarStore((state) => state.setFocusMode);

  const chapters = useCatalogStore((state) => state.chapters);
  const methods = useCatalogStore((state) => state.methods);
  const status = useCatalogStore((state) => state.status);
  const error = useCatalogStore((state) => state.error);
  const load = useCatalogStore((state) => state.load);
  const [isDragging] = useState(false);

  const activeChapterId =
    chapterId ?? methods.find((method) => method.id === methodId)?.chapter;
  const isHidden = !isDrawer && mode === "hidden";

  // Track recent methods when the route changes to a method page.
  useEffect(() => {
    if (methodId && !isRecent(methodId)) {
      addRecent(methodId);
    }
  }, [methodId, isRecent, addRecent]);

  // Ctrl+B / ⌘B cycles sidebar state (expanded → hidden → expanded).
  useEffect(() => {
    if (isDrawer) return;
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if (typing) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        cycle();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [cycle, isDrawer]);

  // F toggles focus mode; Escape exits it.
  useEffect(() => {
    if (isDrawer) return;
    function handleFocusKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if (typing) return;
      if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        setFocusMode(!focusMode);
      } else if (event.key === "Escape") {
        event.preventDefault();
        setFocusMode(false);
      }
    }
    document.addEventListener("keydown", handleFocusKey);
    return () => document.removeEventListener("keydown", handleFocusKey);
  }, [setFocusMode, focusMode, isDrawer]);

  if (status === "loading" || status === "idle") {
    return (
      <div className="space-y-4 px-4 py-5">
        <div className="h-8 w-3/4 skeleton-shimmer rounded-control bg-line" />
        <div className="h-3 w-full skeleton-shimmer rounded-control bg-line" />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="p-3">
        <ErrorState
          compact
          title="Navigation unavailable"
          error={error}
          onRetry={() => void load(true)}
          retryLabel="Retry"
        />
      </div>
    );
  }

  const available = methods.filter((method) => method.status === "available").length;
  const total = methods.length;
  const percent = total === 0 ? 0 : Math.round((available / total) * 100);

  const sidebarClasses = isDrawer
    ? "site-sidebar no-print flex h-full w-full flex-col overflow-hidden bg-[color:var(--color-surface)]"
    : `
    site-sidebar no-print sticky top-16 h-[calc(100dvh-4rem)] shrink-0 overflow-hidden
    bg-[color:var(--color-surface)]/40 backdrop-blur-sm
    ${isDragging ? "" : "transition-[width] duration-150 ease-out"}
    shadow-[inset_-1px_0_0_0_rgb(226_232_240/0.7)] dark:shadow-[inset_-1px_0_0_0_rgb(255_255_255/0.06)]
    ${className ?? ""}
  `;

  const sidebarWidth = isDrawer ? "100%" : isHidden ? 0 : Math.min(420, Math.max(240, width));

  return (
    <>
      {/* Hidden state: floating open handle at left edge */}
      {isHidden && <SidebarOpenHandle />}

      {/* Sidebar itself */}
      <aside
        aria-label="Navigation"
        aria-hidden={isHidden}
        className={sidebarClasses}
        style={{
          width: sidebarWidth,
          minWidth: sidebarWidth,
          maxWidth: sidebarWidth,
          position: isDrawer ? "static" : "sticky",
          zIndex: isDrawer ? undefined : 40,
          left: isDrawer ? undefined : 0,
          top: isDrawer ? undefined : "4rem",
          overflow: "hidden",
        }}
      >
        <div
          className="flex min-h-full w-full flex-col gap-2 px-3 py-2 box-border overflow-y-auto scroll-slim"
          style={{
            minHeight: isDrawer ? "100%" : "calc(100dvh - 4rem)",
            width: sidebarWidth,
            minWidth: sidebarWidth,
            maxWidth: sidebarWidth,
          }}
          inert={isHidden ? true : undefined}
        >
          <div className="w-full px-0">
            <div className="mt-2 w-full space-y-1">
              <div className="w-full rounded-2xl border border-[color:var(--color-accent-soft-line)] bg-[color:var(--color-accent-soft)] p-3" style={{ minWidth: 0 }}>
                <div className="flex items-center justify-between gap-2">
                  <p className={ui.sectionLabel}>Course progress</p>
                  <span className="rounded-full bg-[color:var(--color-surface)] px-2 py-0.5 text-[10px] font-semibold text-[color:var(--color-accent)] ring-1 ring-inset ring-[color:var(--color-accent-soft-line)]">
                    {percent}%
                  </span>
                </div>
                <p className="mt-1.5 text-sm font-semibold text-[color:var(--color-ink)]">
                  {available} of {total} methods ready
                </p>
                <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-[color:var(--color-border)]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-[width] duration-500"
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-[color:var(--color-ink-muted)]">
                  {total - available} syllabus method{total - available === 1 ? "" : "s"} coming soon
                </p>
              </div>
            </div>

            {/* Search field (opens Ctrl-K palette) */}
            <div className="mt-4 w-full" style={{ minWidth: 0 }}>
              <button
                type="button"
                onClick={() => {
                  const event = new KeyboardEvent("keydown", {
                    key: "k",
                    ctrlKey: true,
                    metaKey: true,
                    bubbles: true,
                    cancelable: true,
                  });
                  window.dispatchEvent(event);
                }}
                aria-label="Search methods (Ctrl+K / ⌘K)"
                title="Search methods — Ctrl+K / ⌘K"
                className="flex w-full min-w-0 items-center gap-2 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3.5 py-2.5 text-sm text-left text-[color:var(--color-ink)] transition hover:bg-[color:var(--color-surface-2)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]"
              >
                <Icon name="search" size={16} className="text-[color:var(--color-ink-muted)]" />
                <span className="flex-1 truncate">Search</span>
                <kbd className="shrink-0 rounded border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-1 font-mono text-[10px] text-[color:var(--color-ink-muted)]">
                  Ctrl+K
                </kbd>
              </button>
            </div>

            <div className="mt-4 space-y-1">
              <p className={`px-2 pb-1 ${ui.sectionLabel}`}>Chapters</p>
              {chapters.length === 0 && (
                <EmptyState
                  compact
                  icon="layers"
                  title="No chapters"
                  description="Reload the catalogue to populate the syllabus."
                  action={
                    <button
                      type="button"
                      onClick={() => void load(true)}
                      className={ui.btn}
                    >
                      <Icon name="refresh" size={13} />
                      Reload
                    </button>
                  }
                />
              )}
              {chapters.map((chapter) => (
                <SidebarChapter
                  key={chapter.id}
                  chapter={chapter}
                  methods={methods}
                  activeChapterId={activeChapterId}
                  activeMethodId={methodId}
                  onChapterClick={() => {}}
                  onMethodClick={() => onNavigate?.()}
                  onNavigate={onNavigate}
                />
              ))}
            </div>

            {/* Recent section */}
            {recent.length > 0 && (
              <div className="mt-4 space-y-1">
                <p className={`px-2 pb-1 ${ui.sectionLabel}`}>Recent</p>
                <ul className="space-y-0.5">
                  {recent.map((id) => {
                    const method = methods.find((m) => m.id === id);
                    if (!method) return null;
                    return (
                      <li key={id}>
                        <NavLink
                          to={`/methods/${method.id}`}
                          onClick={() => {
                            addRecent(id);
                            onNavigate?.();
                          }}
                          className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-[11px] transition text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white`}
                          title={method.name}
                        >
                          <span className="min-w-0 flex-1 truncate">{method.name}</span>
                          {isFavorite(id) && (
                            <Icon
                              name="cap"
                              size={11}
                              className="shrink-0 text-amber-500"
                            />
                          )}
                        </NavLink>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {/* Favorites section */}
            {favorites.length > 0 && (
              <div className="mt-4 space-y-1">
                <p className={`px-2 pb-1 ${ui.sectionLabel}`}>Favorites</p>
                <ul className="space-y-0.5">
                  {favorites.map((id) => {
                    const method = methods.find((m) => m.id === id);
                    if (!method) return null;
                    return (
                      <li key={id}>
                        <NavLink
                          to={`/methods/${method.id}`}
                          onClick={() => {
                            toggleFavorite(id);
                            onNavigate?.();
                          }}
                          className={`flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-[11px] transition text-slate-600 hover:bg-slate-100/80 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white`}
                          title={method.name}
                        >
                          <span className="min-w-0 flex-1 truncate">{method.name}</span>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                              toggleFavorite(id);
                            }}
                            aria-label={`Remove ${method.name} from favorites`}
                            className="shrink-0 rounded p-1 text-amber-500 hover:bg-amber-50/50"
                          >
                            <Icon name="cap" size={11} className="text-amber-500" />
                          </button>
                        </NavLink>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            <div className="mt-auto space-y-1 border-t border-slate-200/80 pt-3 dark:border-white/[0.06]">
              <div className="px-2 pb-1">
                <ThemeToggle />
              </div>
              {!isDrawer && (
                <button
                  type="button"
                  onClick={() => setMode("hidden")}
                  aria-label="Hide sidebar"
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
                >
                  <Icon name="chevronLeft" size={14} />
                  Hide sidebar
                </button>
              )}
              <NavLink
                to="/about"
                onClick={onNavigate}
                className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
              >
                <Icon name="info" size={14} />
                About
              </NavLink>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
