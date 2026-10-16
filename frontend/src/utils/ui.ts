/** Shared Tailwind class strings — keeps styling consistent across components. */
export const ui = {
  card: "rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900",
  cardHover:
    "transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md dark:hover:border-indigo-700",
  btn: "inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800",
  btnPrimary:
    "inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-50",
  btnGhost:
    "inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200",
  input:
    "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500",
  inputError: "border-rose-400 focus:border-rose-500 focus:ring-rose-500",
  label: "block text-sm font-medium text-slate-700 dark:text-slate-300",
  help: "mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400",
  error: "mt-1 text-xs text-rose-600 dark:text-rose-400",
} as const;
