import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SidebarMode = "expanded" | "rail" | "hidden";

const MODE_ORDER: SidebarMode[] = ["expanded", "rail", "hidden"];
const STORAGE_KEY = "nms-sidebar";

/** Read the saved sidebar mode synchronously (before first paint). */
export function readSavedSidebarMode(): SidebarMode {
  if (typeof window === "undefined") return "rail";
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as { mode?: SidebarMode };
      if (parsed.mode && MODE_ORDER.includes(parsed.mode)) return parsed.mode;
    }
  } catch {
    // Ignore corrupt/localStorage errors and fall back to default.
  }
  return "rail";
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
      mode: "rail",
      width: 280,
      autoCollapse: true,
      pinned: false,
      recent: [],
      favorites: [],
      focusMode: false,

      setMode: (mode) => set({ mode }),

      cycle: () => {
        const current = get().mode;
        const idx = MODE_ORDER.indexOf(current);
        const next = MODE_ORDER[(idx + 1) % MODE_ORDER.length];
        set({ mode: next, pinned: false });
      },

      setWidth: (width) =>
        set({ width: Math.min(420, Math.max(240, Math.round(width))) }),

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
