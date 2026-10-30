import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "paper" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggle: () => void;
  cycle: () => void;
}

function prefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-color-scheme: dark)").matches === true
  );
}

export function resolveTheme(mode: ThemeMode): "light" | "paper" | "dark" {
  if (mode === "system") {
    return prefersDark() ? "dark" : "light";
  }
  return mode;
}

export function resolveDark(mode: ThemeMode): boolean {
  return resolveTheme(mode) === "dark";
}

/** Apply the resolved theme to <html> */
export function applyTheme(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  const resolved = resolveTheme(mode);
  document.documentElement.setAttribute("data-theme", resolved);
  document.documentElement.classList.toggle("dark", resolved === "dark");
  document.documentElement.style.colorScheme = resolved === "dark" ? "dark" : "light";
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    if (resolved === "dark") meta.setAttribute("content", "#0B0D12");
    else if (resolved === "paper") meta.setAttribute("content", "#FAF7F0");
    else meta.setAttribute("content", "#FBFBFC");
  }
}

const CYCLE: ThemeMode[] = ["light", "paper", "dark", "system"];

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: "system",
      setMode: (mode) => {
        applyTheme(mode);
        set({ mode });
      },
      toggle: () => {
        const current = get().mode;
        const resolved = resolveTheme(current);
        const next: ThemeMode = resolved === "dark" ? "light" : "dark";
        applyTheme(next);
        set({ mode: next });
      },
      cycle: () => {
        const current = get().mode;
        const idx = CYCLE.indexOf(current);
        const next = CYCLE[(idx + 1) % CYCLE.length];
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

export function initThemeListener(): () => void {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const listener = (): void => {
    const mode = useThemeStore.getState().mode;
    if (mode === "system") applyTheme(mode);
  };
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}
