/** Shared Tailwind class strings — all values resolve to tokens in design/tokens.css. */
export const ui = {
  card: "rounded-panel border border-line bg-surface shadow-card",
  cardHover:
    "transition duration-200 hover:-translate-y-0.5 hover:border-accent-300 hover:shadow-popover",
  surface: "rounded-control border border-line bg-surface-muted",
  btn: "inline-flex items-center justify-center gap-2 rounded-control border border-line-strong bg-surface px-3.5 py-2 text-sm font-medium text-ink shadow-sm transition duration-150 hover:border-ink-subtle hover:bg-surface-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50",
  btnPrimary:
    "inline-flex items-center justify-center gap-2 rounded-control bg-accent-solid px-4 py-2.5 text-sm font-semibold text-white shadow-accent transition duration-150 hover:bg-accent-solid-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-60",
  btnGhost:
    "inline-flex items-center gap-1.5 rounded-control px-2 py-1.5 text-xs font-medium text-ink-muted transition duration-150 hover:bg-surface-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500",
  input:
    "w-full rounded-control border border-line-strong bg-surface px-3.5 py-2.5 text-sm text-ink shadow-sm transition duration-150 placeholder:text-ink-subtle focus:border-accent-500 focus:outline-none focus:ring-4 focus:ring-accent-500/10",
  inputError: "border-danger focus:border-danger focus:ring-danger/15",
  label: "block text-sm font-medium text-ink",
  help: "mt-1.5 text-xs leading-relaxed text-ink-muted",
  error: "mt-1.5 text-xs font-medium text-danger",
  chip: "inline-flex items-center gap-1.5 rounded-pill border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-muted shadow-sm transition duration-150 hover:border-accent-300 hover:text-accent-text",
  sectionLabel:
    "text-2xs font-semibold uppercase tracking-[0.14em] text-ink-muted",
  iconBox:
    "inline-flex shrink-0 items-center justify-center rounded-control bg-accent-soft text-accent-text ring-1 ring-inset ring-accent-soft-line",
  num: "font-mono tabular-nums",
  muted: "text-ink-muted",
} as const;
