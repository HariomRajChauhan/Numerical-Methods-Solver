/** Shared Tailwind class strings — keeps styling consistent across components. */
export const ui = {
  card: "rounded-2xl border border-slate-200/80 bg-white shadow-sm shadow-slate-900/[0.03] dark:border-white/[0.07] dark:bg-slate-900/60 dark:shadow-none",
  cardHover:
    "transition duration-200 hover:-translate-y-0.5 hover:border-indigo-300/80 hover:shadow-lg hover:shadow-indigo-500/[0.06] dark:hover:border-indigo-400/30",
  surface:
    "rounded-xl border border-slate-200/80 bg-slate-50/70 dark:border-white/[0.06] dark:bg-slate-950/40",
  btn: "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/10 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-white/20 dark:hover:bg-slate-800 dark:focus-visible:ring-offset-slate-950",
  btnPrimary:
    "inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition hover:bg-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:focus-visible:ring-offset-slate-950",
  btnGhost:
    "inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 dark:text-slate-300 dark:hover:bg-white/[0.06] dark:hover:text-white",
  input:
    "w-full rounded-xl border border-slate-300/90 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm transition placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 dark:border-white/10 dark:bg-slate-950/50 dark:text-slate-100 dark:placeholder:text-slate-400 dark:focus:border-indigo-400 dark:focus:ring-indigo-400/10",
  inputError:
    "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15 dark:border-rose-500/70",
  label: "block text-sm font-medium text-slate-700 dark:text-slate-200",
  help: "mt-1.5 text-xs leading-relaxed text-slate-600 dark:text-slate-400",
  error: "mt-1.5 text-xs font-medium text-rose-600 dark:text-rose-400",
  chip: "inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-indigo-300 hover:text-indigo-700 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300 dark:hover:border-indigo-400/40 dark:hover:text-indigo-300",
  sectionLabel:
    "text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600 dark:text-slate-400",
  iconBox:
    "inline-flex shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20",
} as const;
