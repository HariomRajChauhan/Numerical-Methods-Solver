import type { IconName } from "../components/ui/Icon";
import type { ChapterId } from "../types/api";

export interface ChapterVisual {
  icon: IconName;
  /** Gradient used by the chapter mark. */
  gradient: string;
  /** Soft tinted surface for icons and badges. */
  tint: string;
  /** Accent text colour that pairs with the tint. */
  accent: string;
  /** Soft border used by chapter hero panels. */
  border: string;
}

const FALLBACK: ChapterVisual = {
  icon: "book",
  gradient: "from-indigo-500 to-violet-500",
  tint: "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300",
  accent: "text-indigo-600 dark:text-indigo-300",
  border: "border-indigo-200/70 dark:border-indigo-400/20",
};

/** Icons and accent colours for every syllabus chapter (stable across the app). */
export const CHAPTER_VISUALS: Record<ChapterId, ChapterVisual> = {
  ch1_nonlinear: {
    icon: "target",
    gradient: "from-indigo-500 to-violet-500",
    tint: "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300",
    accent: "text-indigo-600 dark:text-indigo-300",
    border: "border-indigo-200/70 dark:border-indigo-400/20",
  },
  ch2_linear: {
    icon: "grid",
    gradient: "from-sky-500 to-cyan-500",
    tint: "bg-sky-50 text-sky-600 dark:bg-sky-500/10 dark:text-sky-300",
    accent: "text-sky-600 dark:text-sky-300",
    border: "border-sky-200/70 dark:border-sky-400/20",
  },
  ch3_interpolation: {
    icon: "chart",
    gradient: "from-emerald-500 to-teal-500",
    tint: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300",
    accent: "text-emerald-600 dark:text-emerald-300",
    border: "border-emerald-200/70 dark:border-emerald-400/20",
  },
  ch4_diff_integration: {
    icon: "integral",
    gradient: "from-amber-500 to-orange-500",
    tint: "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-300",
    accent: "text-amber-600 dark:text-amber-300",
    border: "border-amber-200/70 dark:border-amber-400/20",
  },
  ch5_ode: {
    icon: "wave",
    gradient: "from-rose-500 to-pink-500",
    tint: "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-300",
    accent: "text-rose-600 dark:text-rose-300",
    border: "border-rose-200/70 dark:border-rose-400/20",
  },
  ch6_pde: {
    icon: "layers",
    gradient: "from-fuchsia-500 to-purple-500",
    tint: "bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-500/10 dark:text-fuchsia-300",
    accent: "text-fuchsia-600 dark:text-fuchsia-300",
    border: "border-fuchsia-200/70 dark:border-fuchsia-400/20",
  },
};

export function chapterVisual(chapterId: string | undefined): ChapterVisual {
  if (!chapterId) return FALLBACK;
  return CHAPTER_VISUALS[chapterId as ChapterId] ?? FALLBACK;
}
