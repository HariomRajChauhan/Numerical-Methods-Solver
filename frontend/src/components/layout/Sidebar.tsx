import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation, useParams } from "react-router-dom";

import { useCatalogStore } from "../../store/catalog";
import { useSidebarStore } from "../../store/sidebar";
import { chapterVisual } from "../../utils/chapters";
import { ui } from "../../utils/ui";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Icon } from "../ui/Icon";
import { SidebarChapter } from "./SidebarChapter";
import { SidebarFlyout } from "./SidebarFlyout";
import { SidebarOpenHandle } from "./SidebarOpenHandle";
import { SidebarResizeHandle } from "./SidebarResizeHandle";
import { ThemeToggle } from "./ThemeToggle";
import type { ChapterInfo } from "../../types/api";

interface SidebarProps {
  /** Called after navigation on mobile (to close the drawer). */
  onNavigate?: () => void;
}

/**
 * Sidebar with three states:
 *  - expanded: 280 px (resizable 240–420), full chapter > method tree
 *  - rail: 56 px, icon-only chapters with flyout on click
 *  - hidden: 0 px, floating open handle at left edge
 *
 * Cycles with Ctrl+B / ⌘B. State and width persist to localStorage.
 * Default: rail.
 */
export function Sidebar({ onNavigate }: SidebarProps) {
  const { chapterId, methodId } = useParams<{ chapterId?: string; methodId?: string }>();
  const location = useLocation();

  const mode = useSidebarStore((state) => state.mode);
  const width = useSidebarStore((state) => state.width);
  const autoCollapse = useSidebarStore((state) => state.autoCollapse);
  const pinned = useSidebarStore((state) => state.pinned);
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

  const [flyoutChapter, setFlyoutChapter] = useState<ChapterInfo | null>(null);
  const [railHovered, setRailHovered] = useState(false);
  const railHoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [overlayActive, setOverlayActive] = useState(false);
  const [isDragging] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const width = window.innerWidth;
    if (width < 1280 && mode === "expanded") {
      setMode("rail");
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function handleResize() {
      if (window.innerWidth < 1280 && mode === "expanded" && !pinned) {
        setMode("rail");
      }
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [mode, pinned, setMode]);

  const activeChapterId =
    chapterId ?? methods.find((method) => method.id === methodId)?.chapter;
  const isRail = mode === "rail";
  const isHidden = mode === "hidden";

  // Auto-collapse to rail when opening a method page.
  useEffect(() => {
    if (autoCollapse && location.pathname.startsWith("/methods/") && mode === "expanded" && !pinned) {
      setMode("rail");
    }
  }, [location, autoCollapse, mode, pinned, setMode]);

  // Rail hover overlay: expand after 400 ms hover, collapse on leave.
  // setOverlayActive(false) is called from event handlers (onMouseLeave,
  // pin button, backdrop click) rather than here, to avoid calling setState
  // directly in the effect body.
  useEffect(() => {
    if (!isRail || pinned || !railHovered) {
      if (railHoverTimer.current) clearTimeout(railHoverTimer.current);
      return;
    }

    railHoverTimer.current = setTimeout(() => {
      setOverlayActive(true);
    }, 400);

    return () => {
      if (railHoverTimer.current) clearTimeout(railHoverTimer.current);
    };
  }, [isRail, pinned, railHovered]);

  // Track recent methods when the route changes to a method page.
  useEffect(() => {
    if (methodId && !isRecent(methodId)) {
      addRecent(methodId);
    }
  }, [methodId, isRecent, addRecent]);

  // Ctrl+B / ⌘B cycles sidebar state (expanded → rail → hidden → expanded).
  useEffect(() => {
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
  }, [cycle]);

  // F toggles focus mode; Escape exits it.
  useEffect(() => {
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
  }, [setFocusMode, focusMode]);

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

  const sidebarClasses = `
    site-sidebar no-print sticky top-16 h-[calc(100dvh-4rem)] shrink-0 overflow-hidden
    w-[56px]
    bg-white/40 backdrop-blur-sm
    dark:bg-[#070a13]/30
    ${isDragging ? "" : "transition-[width] duration-150 ease-out"}
    shadow-[inset_-1px_0_0_0_rgb(226_232_240/0.7)] dark:shadow-[inset_-1px_0_0_0_rgb(255_255_255/0.06)]
  `;

  // Width per state - derived from single source of truth
  const sidebarWidth =
    isHidden ? 0 : isRail ? (overlayActive && !pinned ? 280 : 56) : Math.min(420, Math.max(240, width));
  const innerWidth = isRail ? 56 : isHidden ? 0 : Math.min(420, Math.max(240, width));

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
          // When in rail overlay mode, position absolutely over content
          position: overlayActive && !pinned ? "absolute" : "sticky",
          zIndex: overlayActive && !pinned ? 50 : 40,
          left: 0,
          top: "4rem",
          boxShadow: overlayActive && !pinned
            ? "0 18px 48px -24px rgb(15 23 42 / 0.32)"
            : undefined,
          overflow: "hidden",
        }}
      >
        <div
          className="flex min-h-full w-full flex-col gap-2 px-3 py-2 box-border overflow-hidden"
          style={{ minHeight: "calc(100dvh - 4rem)", width: innerWidth, minWidth: innerWidth, maxWidth: innerWidth }}
          inert={isHidden ? true : undefined}
        >
          {!isRail && (
            <div className="w-full px-0">
              <div className="mt-2 w-full space-y-1">
                <div className="w-full rounded-2xl border border-indigo-200/60 bg-gradient-to-br from-indigo-50 via-white to-white p-3 dark:border-indigo-400/15 dark:from-indigo-500/[0.08] dark:via-transparent dark:to-transparent" style={{ minWidth: 0 }}>
                  <div className="flex items-center justify-between gap-2">
                    <p className={ui.sectionLabel}>Course progress</p>
                    <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-indigo-600 ring-1 ring-inset ring-indigo-200/70 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20">
                      {percent}%
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {available} of {total} methods ready
                  </p>
                  <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-slate-200/80 dark:bg-white/[0.08]">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-[width] duration-500"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
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
                  className="flex w-full min-w-0 items-center gap-2 rounded-xl border border-line-strong bg-surface px-3.5 py-2.5 text-sm text-left text-ink shadow-sm transition hover:bg-surface-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
                >
                  <Icon name="search" size={16} className="text-slate-400" />
                  <span className="flex-1 truncate">Search</span>
                  <kbd className="shrink-0 rounded border border-line bg-surface-muted px-1 font-mono text-[10px] text-slate-500">
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
                    isRail={false}
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
                <button
                  type="button"
                  onClick={() => setMode("rail")}
                  aria-label="Collapse sidebar to rail"
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
                >
                  <Icon name="chevronLeft" size={14} />
                  Collapse
                </button>
                <button
                  type="button"
                  onClick={() => setMode("hidden")}
                  aria-label="Hide sidebar"
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
                >
                  <Icon name="chevronLeft" size={14} />
                  Hide
                </button>
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
          )}

          {/* Rail state: icon-only chapters */}
          {isRail && (
            <div className="flex flex-1 flex-col items-center gap-2 overflow-hidden pt-2" style={{ width: 56, minWidth: 56, maxWidth: 56, boxSizing: "border-box" }}>
              <NavLink to="/" onClick={onNavigate} aria-label="Home" title="Home" className={`relative flex h-10 w-10 items-center justify-center rounded-xl transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${location.pathname === "/" ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"}`}>
                {location.pathname === "/" && <span className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r bg-indigo-500" />}
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m3 10 9-7 9 7v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9Z" />
                  <path d="M9 21v-7h6v7" />
                </svg>
              </NavLink>
              <div className="flex flex-col items-center gap-2 overflow-hidden">
                {chapters.map((chapter) => {
                  const visual = chapterVisual(chapter.id);
                  const isActiveChapter = activeChapterId === chapter.id;
                  const tooltip = `${chapter.title} · ${chapter.available_count}/${chapter.method_count} methods ready`;
                  return (
                    <button
                      key={chapter.id}
                      type="button"
                      aria-label={chapter.title}
                      aria-expanded={flyoutChapter?.id === chapter.id}
                      aria-current={isActiveChapter ? "true" : undefined}
                      onClick={() => {
                        setFlyoutChapter(flyoutChapter?.id === chapter.id ? null : chapter);
                        setOverlayActive(false);
                      }}
                      onFocus={() => {
                        setRailHovered(true);
                        if (!pinned) {
                          if (railHoverTimer.current) clearTimeout(railHoverTimer.current);
                          railHoverTimer.current = setTimeout(() => setOverlayActive(true), 400);
                        }
                      }}
                      onBlur={(e) => {
                        if (e.currentTarget.contains(e.relatedTarget as Node)) return;
                        setRailHovered(false);
                        if (railHoverTimer.current) clearTimeout(railHoverTimer.current);
                        setOverlayActive(false);
                      }}
                      onMouseEnter={() => {
                        setRailHovered(true);
                        if (!pinned) {
                          if (railHoverTimer.current) clearTimeout(railHoverTimer.current);
                          railHoverTimer.current = setTimeout(() => setOverlayActive(true), 400);
                        }
                      }}
                      onMouseLeave={() => {
                        setRailHovered(false);
                        if (railHoverTimer.current) clearTimeout(railHoverTimer.current);
                        setOverlayActive(false);
                      }}
                      title={tooltip}
                      className={`group relative flex h-10 w-10 items-center justify-center rounded-xl transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${
                        isActiveChapter
                          ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
                      }`}
                    >
                      {isActiveChapter && <span className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r bg-indigo-500" />}
                      <span className="flex h-5 w-5 items-center justify-center">
                        {chapter.id === "ch4_diff_integration" ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="block">
                            <path d="M15.5 4c-2 0-3 1.2-3 3.2V17c0 2-1 3-3 3" />
                            <path d="M9.5 8h5" />
                          </svg>
                        ) : (
                          <Icon name={visual.icon} size={20} />
                        )}
                      </span>
                      <span className="pointer-events-none absolute left-[calc(100%+8px)] top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 dark:bg-white dark:text-slate-900">
                        {tooltip}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="mt-auto flex flex-col items-center gap-2 pb-2">
                <button
                  type="button"
                  onClick={() => {
                    const event = new KeyboardEvent("keydown", { key: "k", ctrlKey: true, metaKey: true, bubbles: true, cancelable: true });
                    window.dispatchEvent(event);
                  }}
                  aria-label="Search"
                  title="Search (Ctrl+K)"
                  className="flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="7" />
                    <path d="m20 20-3.6-3.6" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => setMode("expanded")}
                  aria-label="Favorites"
                  title="Favorites"
                  className="flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-white"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m12 3 1.9 5.8H20l-5 3.6 1.9 5.8-5-3.6-5 3.6 1.9-5.8-5-3.6h6.1L12 3Z" />
                  </svg>
                </button>
                <div className="flex h-10 w-10 items-center justify-center">
                  <ThemeToggle />
                </div>
              </div>
            </div>
          )}


          {isRail && flyoutChapter && (
            <SidebarFlyout
              chapter={flyoutChapter}
              methods={methods}
              activeMethodId={methodId}
              isOpen={true}
              onClose={() => setFlyoutChapter(null)}
              onMethodClick={() => {
                setFlyoutChapter(null);
                onNavigate?.();
              }}
            />
          )}
        </div>

        {!isHidden && <SidebarResizeHandle />}
      </aside>

      {/* Rail overlay: semi-transparent backdrop to close on click */}
      {overlayActive && !flyoutChapter && (
        <div
          role="presentation"
          onClick={() => setOverlayActive(false)}
          className="fixed inset-0 z-30 bg-black/5"
          aria-hidden="true"
        />
      )}
    </>
  );
}
