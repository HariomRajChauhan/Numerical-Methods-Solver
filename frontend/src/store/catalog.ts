import { create } from "zustand";

import { api, ApiError } from "../api/client";
import type { ChapterInfo, MethodCatalog, MethodMeta } from "../types/api";

interface CatalogState {
  chapters: ChapterInfo[];
  methods: MethodMeta[];
  status: "idle" | "loading" | "ready" | "error";
  error?: ApiError;
  /** Fetch the catalogue once (cached afterwards unless force=true). */
  load: (force?: boolean) => Promise<void>;
}

export const useCatalogStore = create<CatalogState>()((set, get) => ({
  chapters: [],
  methods: [],
  status: "idle",
  error: undefined,
  load: async (force = false) => {
    const { status } = get();
    if (!force && (status === "loading" || status === "ready")) return;
    set({ status: "loading", error: undefined });
    try {
      const catalog: MethodCatalog = await api.getCatalog();
      set({
        chapters: catalog.chapters,
        methods: catalog.methods,
        status: "ready",
        error: undefined,
      });
    } catch (error) {
      set({
        status: "error",
        error: error instanceof ApiError ? error : new ApiError("Failed to load methods."),
      });
    }
  },
}));

/** Methods belonging to one chapter (sorted: available first, then name). */
export function selectChapterMethods(methods: MethodMeta[], chapterId: string): MethodMeta[] {
  return methods
    .filter((method) => method.chapter === chapterId)
    .sort((a, b) => {
      if (a.status !== b.status) return a.status === "available" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
}

export function selectChapter(chapters: ChapterInfo[], chapterId: string): ChapterInfo | undefined {
  return chapters.find((chapter) => chapter.id === chapterId);
}

/** Case-insensitive search over name, summary and chapter title. */
export function searchMethods(methods: MethodMeta[], query: string): MethodMeta[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];

  function score(method: MethodMeta): number {
    const name = method.name.toLowerCase();
    if (name === needle) return 5;
    if (name.startsWith(needle)) return 4;
    if (name.includes(needle)) return 3;
    if (method.id.includes(needle)) return 2;
    if (method.chapter_title.toLowerCase().includes(needle)) return 1;
    return 0;
  }

  return methods
    .filter((method) =>
      [method.name, method.summary, method.chapter_title, method.id]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    )
    .sort((a, b) => score(b) - score(a) || a.name.localeCompare(b.name));
}
