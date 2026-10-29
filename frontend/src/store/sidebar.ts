import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SidebarMode = "expanded" | "rail" | "hidden";

const MODE_ORDER: SidebarMode[] = ["expanded", "rail", "hidden"];
export const STORAGE_KEY = "nms-sidebar";

function sanitizeMode(mode: unknown): SidebarMode {
  if (typeof mode === "string" && MODE_ORDER.includes(mode as SidebarMode)) {
    return mode as SidebarMode;
  }
  return "rail";
}

function sanitizeWidth(width: unknown): number {
  const w = typeof width === "number" ? width : 280;
  return Math.min(420, Math.max(240, Math.round(w)));
}

/** Read the saved sidebar mode synchronously (before first paint). */
export function readSavedSidebarMode(): SidebarMode {
  if (typeof window === "undefined") return "rail";
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: { mode?: unknown; width?: unknown }; mode?: unknown; width?: unknown };
      const mode = parsed.state?.mode ?? parsed.mode;
      return sanitizeMode(mode);
    }
  } catch {
    // Ignore corrupt/localStorage errors and fall back to default.
  }
  return "rail";
}

export function readSavedSidebarWidth(): number {
  if (typeof window === "undefined") return 280;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: { mode?: unknown; width?: unknown }; mode?: unknown; width?: unknown };
      const mode = sanitizeMode(parsed.state?.mode ?? parsed.mode);
      if (mode !== "expanded") return 280;
      const width = parsed.state?.width ?? parsed.width;
      return sanitizeWidth(width);
    }
  } catch {
    // Ignore corrupt/localStorage errors and fall back to default.
  }
  return 280;
}

interface SidebarState {
  mode: SidebarMode;
  width: number;
  autoCollapse: boolean;
  pinned: boolean;
  recent: string[];
  favorites: string[];
  focusMode: boolean;

  setMode: (mode: SidebarMode) => void;
  cycle: () => void;
  setWidth: (width: number) => void;
  setAutoCollapse: (v: boolean) => void;
  setPinned: (v: boolean) => void;
  addRecent: (id: string) => void;
  toggleFavorite: (id: string) => void;
  removeRecent: (id: string) => void;
  setFocusMode: (v: boolean) => void;
  isFavorite: (id: string) => boolean;
  isRecent: (id: string) => boolean;
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set, get) => ({
      mode: typeof window === "undefined" ? "rail" : readSavedSidebarMode(),
      width: typeof window === "undefined" ? 280 : readSavedSidebarWidth(),
      autoCollapse: true,
      pinned: false,
      recent: [],
      favorites: [],
      focusMode: false,

      setMode: (mode) => {
        const m = sanitizeMode(mode);
        if (m === "expanded") {
          set({ mode: m, width: sanitizeWidth(get().width) });
        } else {
          set({ mode: m });
        }
      },

      cycle: () => {
        const current = sanitizeMode(get().mode);
        const idx = MODE_ORDER.indexOf(current);
        const next = MODE_ORDER[(idx + 1) % MODE_ORDER.length];
        set({ mode: next, pinned: false });
        if (next === "expanded") {
          set({ width: sanitizeWidth(get().width) });
        }
      },

      setWidth: (width) => {
        set({ width: sanitizeWidth(width) });
      },

      setAutoCollapse: (v) => set({ autoCollapse: v }),

      setPinned: (v) => set({ pinned: v }),

      addRecent: (id) => {
        const recent = get().recent;
        const next = [id, ...recent.filter((x) => x !== id)].slice(0, 5);
        set({ recent: next });
      },

      toggleFavorite: (id) => {
        const favorites = new Set(get().favorites);
        if (favorites.has(id)) favorites.delete(id);
        else favorites.add(id);
        set({ favorites: [...favorites] });
      },

      removeRecent: (id) => {
        set({ recent: get().recent.filter((x) => x !== id) });
      },

      setFocusMode: (v) => set({ focusMode: v }),

      isFavorite: (id) => get().favorites.includes(id),

      isRecent: (id) => get().recent.includes(id),
    }),
    { name: STORAGE_KEY }
  )
);
