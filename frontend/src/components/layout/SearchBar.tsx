import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { searchMethods, useCatalogStore } from "../../store/catalog";
import { ui } from "../../utils/ui";
import { MethodStatusBadge } from "../StatusBadge";
import { Icon } from "../ui/Icon";

/**
 * Global method search with a command-palette feel: click, ⌘K / Ctrl-K or “/”
 * to focus, arrow keys to move, Enter to open and Esc to dismiss.
 */
export function SearchBar() {
  const methods = useCatalogStore((state) => state.methods);
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => searchMethods(methods, query).slice(0, 8), [methods, query]);
  const trimmed = query.trim();
  const showResults = open && trimmed !== "";
  const activeIndex = results.length === 0 ? 0 : Math.min(active, results.length - 1);

  useEffect(() => {
    if (!showResults) return;
    document
      .getElementById(`search-result-${activeIndex}`)
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [activeIndex, showResults]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent): void {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleShortcut(event: KeyboardEvent): void {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
        setOpen(true);
      } else if (event.key === "/" && !typing) {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleShortcut);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleShortcut);
    };
  }, []);

  function goTo(methodId: string): void {
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
    navigate(`/methods/${methodId}`);
  }

  function move(step: number): void {
    if (results.length === 0) return;
    setOpen(true);
    setActive((current) => {
      const base = Math.min(current, results.length - 1);
      return (base + step + results.length) % results.length;
    });
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full max-w-xl"
      onBlur={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
        // Defer so a click/scroll inside the palette can finish first.
        window.setTimeout(() => {
          if (!containerRef.current?.contains(document.activeElement)) setOpen(false);
        }, 0);
      }}
    >
      <label htmlFor="method-search" className="sr-only">
        Search methods
      </label>
      <div className="relative">
        <Icon
          name="search"
          size={17}
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500"
        />
        <input
          ref={inputRef}
          id="method-search"
          type="search"
          role="combobox"
          aria-expanded={showResults}
          aria-controls="method-search-results"
          aria-autocomplete="list"
          aria-activedescendant={
            showResults && results.length > 0 ? `search-result-${activeIndex}` : undefined
          }
          autoComplete="off"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              move(1);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              move(-1);
            } else if (event.key === "Enter" && results.length > 0) {
              event.preventDefault();
              goTo(results[activeIndex].id);
            } else if (event.key === "Escape") {
              setOpen(false);
              inputRef.current?.blur();
            }
          }}
          placeholder="Search methods — Newton, Simpson, RK4…"
          className={`${ui.input} !py-2 pl-10 pr-16 [&::-webkit-search-cancel-button]:hidden`}
        />
        {trimmed === "" ? (
          <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 items-center gap-0.5 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-600 sm:flex dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300">
            ⌘K
          </kbd>
        ) : (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
            aria-label="Clear search"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-white/[0.06] dark:hover:text-slate-200"
          >
            <Icon name="close" size={14} />
          </button>
        )}
      </div>

      {showResults && (
        <div className="fixed left-1/2 top-[4.5rem] z-50 w-[calc(100vw-2rem)] max-w-[34rem] -translate-x-1/2 overflow-hidden rounded-2xl border border-slate-200/90 bg-white/95 shadow-2xl shadow-slate-900/10 backdrop-blur-xl lg:absolute lg:left-0 lg:right-0 lg:top-full lg:mt-2 lg:w-auto lg:max-w-none lg:translate-x-0 dark:border-white/10 dark:bg-slate-900/95 dark:shadow-black/40">
          <div
            id="method-search-results"
            role="listbox"
            aria-label="Search results"
            className="max-h-[min(22rem,calc(100dvh-8rem))] overflow-y-auto p-1.5 scroll-slim"
          >
            {results.length === 0 ? (
              <div className="flex items-start gap-3 px-3 py-4">
                <span className="mt-0.5 text-slate-400">
                  <Icon name="search" size={18} />
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    No methods match “{trimmed}”
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Try a method name, a chapter or a keyword such as “root” or “integral”.
                  </p>
                </div>
              </div>
            ) : (
              results.map((method, index) => (
                <button
                  key={method.id}
                  id={`search-result-${index}`}
                  type="button"
                  role="option"
                  aria-selected={index === activeIndex}
                  tabIndex={-1}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => goTo(method.id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                    index === activeIndex
                      ? "bg-indigo-50 dark:bg-indigo-500/10"
                      : "hover:bg-slate-50 dark:hover:bg-white/[0.03]"
                  }`}
                >
                  <span
                    className={`hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[11px] font-semibold sm:flex ${
                      index === activeIndex
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-600 dark:bg-white/[0.06] dark:text-slate-300"
                    }`}
                  >
                    {method.chapter_number}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                      {method.name}
                    </span>
                    <span className="block truncate text-xs text-slate-600 dark:text-slate-400">
                      {method.chapter_title}
                    </span>
                  </span>
                  {method.status === "coming_soon" && (
                    <MethodStatusBadge status="coming_soon" />
                  )}
                  <Icon
                    name="arrowRight"
                    size={15}
                    className={`shrink-0 ${
                      index === activeIndex
                        ? "text-indigo-500 dark:text-indigo-300"
                        : "text-slate-300 dark:text-slate-600"
                    }`}
                  />
                </button>
              ))
            )}
          </div>
          {results.length > 0 && (
            <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-4 py-2 text-[11px] text-slate-600 dark:border-white/[0.06] dark:text-slate-400">
              <span>
                {results.length} result{results.length === 1 ? "" : "s"}
              </span>
              <span className="hidden items-center gap-2 sm:flex">
                <kbd className="rounded border border-slate-200 px-1 dark:border-white/10">↑</kbd>
                <kbd className="rounded border border-slate-200 px-1 dark:border-white/10">↓</kbd>
                to move
                <kbd className="ml-1 rounded border border-slate-200 px-1 dark:border-white/10">
                  ↵
                </kbd>
                to open
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
