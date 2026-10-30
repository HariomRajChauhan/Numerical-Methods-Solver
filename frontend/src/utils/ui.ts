/** Shared Tailwind class strings — all values resolve to tokens in design/tokens.css. */
export const ui = {
  card: "rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)]",
  cardHover:
    "transition duration-150 hover:border-[color:var(--color-accent)]",
  surface: "rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)]",
  btn: "inline-flex items-center justify-center gap-2 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3.5 py-2 text-sm font-medium text-[color:var(--color-ink)] transition duration-150 hover:border-[color:var(--color-ink-muted)] hover:bg-[color:var(--color-surface-2)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-50",
  btnPrimary:
    "inline-flex items-center justify-center gap-2 rounded-md bg-[color:var(--color-accent)] px-4 py-2.5 text-sm font-semibold text-white transition duration-150 hover:bg-[color:var(--color-accent-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-60",
  btnGhost:
    "inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-[color:var(--color-ink-muted)] transition duration-150 hover:bg-[color:var(--color-surface-2)] hover:text-[color:var(--color-ink)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent)]",
  input:
    "w-full rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3.5 py-2.5 text-sm text-[color:var(--color-ink)] transition duration-150 placeholder:text-[color:var(--color-ink-muted)] focus:border-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-focus-ring)]",
  inputError: "border-[color:var(--color-error)] focus:border-[color:var(--color-error)] focus:ring-[color:var(--color-error)]",
  label: "block text-sm font-medium text-[color:var(--color-ink)]",
  help: "mt-1.5 text-xs leading-relaxed text-[color:var(--color-ink-muted)]",
  error: "mt-1.5 text-xs font-medium text-[color:var(--color-error)]",
  chip: "inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-ink-muted)] transition duration-150 hover:border-[color:var(--color-accent)] hover:text-[color:var(--color-ink)]",
  sectionLabel:
    "text-2xs font-semibold uppercase tracking-[0.14em] text-[color:var(--color-ink-muted)]",
  iconBox:
    "inline-flex shrink-0 items-center justify-center rounded-md bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent)] ring-1 ring-inset ring-[color:var(--color-accent-soft)]",
  num: "font-mono tabular-nums",
  muted: "text-[color:var(--color-ink-muted)]",
} as const;
