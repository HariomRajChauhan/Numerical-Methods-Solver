import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggle: () => void;
}

function prefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-color-scheme: dark)").matches === true
  );
}

/** Resolve whether a theme mode currently means "dark". */
export function resolveDark(mode: ThemeMode): boolean {
  return mode === "dark" || (mode === "system" && prefersDark());
}

/** Apply the resolved theme to <html> (Tailwind dark variant is class-based). */
export function applyTheme(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  const dark = resolveDark(mode);
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: "system",
      setMode: (mode) => {
        applyTheme(mode);
        set({ mode });
      },
      toggle: () => {
        const next: ThemeMode = get().mode === "dark" ? "light" : "dark";
        applyTheme(next);
        set({ mode: next });
      },
    }),
    {
      name: "nms-theme",
      onRehydrateStorage: () => (state) => {
        applyTheme(state?.mode ?? "system");
      },
    },
  ),
);

/** React to OS theme changes while in "system" mode. */
export function initThemeListener(): () => void {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const listener = (): void => applyTheme(useThemeStore.getState().mode);
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}
