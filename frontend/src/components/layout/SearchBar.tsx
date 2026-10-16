import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { searchMethods, useCatalogStore } from "../../store/catalog";
import { ui } from "../../utils/ui";
import { MethodStatusBadge } from "../StatusBadge";

/** Global method search: filters name/summary/chapter and jumps to the method. */
export function SearchBar() {
  const methods = useCatalogStore((state) => state.methods);
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => searchMethods(methods, query).slice(0, 8), [methods, query]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent): void {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function goTo(methodId: string): void {
    setQuery("");
    setOpen(false);
    navigate(`/methods/${methodId}`);
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <label htmlFor="method-search" className="sr-only">
        Search methods
      </label>
      <input
        id="method-search"
        type="search"
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls="method-search-results"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && results.length > 0) goTo(results[0].id);
          if (event.key === "Escape") setOpen(false);
        }}
        placeholder="Search methods (e.g. Newton, Simpson…)"
        className={ui.input}
      />
      {open && query.trim() !== "" && (
        <ul
          id="method-search-results"
          role="listbox"
          className={`absolute z-20 mt-1 max-h-80 w-full overflow-auto py-1 ${ui.card}`}
        >
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500">No methods match “{query}”.</li>
          )}
          {results.map((method) => (
            <li key={method.id} role="option" aria-selected={false}>
              <button
                type="button"
                onClick={() => goTo(method.id)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm transition hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <span>
                  <span className="font-medium">{method.name}</span>
                  <span className="ml-2 text-xs text-slate-500">{method.chapter_title}</span>
                </span>
                <MethodStatusBadge status={method.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
