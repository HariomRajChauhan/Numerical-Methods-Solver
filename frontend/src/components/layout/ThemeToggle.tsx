import { useThemeStore, type ThemeMode } from "../../store/theme";
import { Icon, type IconName } from "../ui/Icon";

const MODES: { id: ThemeMode; label: string; icon: IconName }[] = [
  { id: "light", label: "Utility Light", icon: "sun" },
  { id: "paper", label: "Academic Paper", icon: "book" },
  { id: "dark", label: "Developer Dark", icon: "moon" },
  { id: "system", label: "System", icon: "monitor" },
];

/** Theme switcher for all three themes + system. */
export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const mode = useThemeStore((state) => state.mode);
  const setMode = useThemeStore((state) => state.setMode);
  const cycle = useThemeStore((state) => state.cycle);

  if (compact) {
    return (
      <button
        type="button"
        onClick={cycle}
        aria-label="Cycle theme"
        title="Cycle theme"
        className="flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 dark:text-slate-400 dark:hover:bg-white/4 dark:hover:text-white"
      >
        {mode === "light" && <Icon name="sun" size={20} />}
        {mode === "paper" && <Icon name="book" size={20} />}
        {mode === "dark" && <Icon name="moon" size={20} />}
        {mode === "system" && <Icon name="monitor" size={20} />}
        <span className="sr-only">Cycle theme</span>
      </button>
    );
  }

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className="inline-flex shrink-0 items-center gap-0.5 rounded-xl border border-border bg-surface-2 p-0.5"
    >
      {MODES.map((option) => {
        const active = mode === option.id;
        return (
          <button
            key={option.id}
            type="button"
            onClick={() => setMode(option.id)}
            aria-pressed={active}
            title={`${option.label} theme`}
            className={`flex h-8 w-8 items-center justify-center rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${
              active
                ? "bg-surface text-ink"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            <Icon name={option.icon} size={18} />
            <span className="sr-only">{option.label} theme</span>
          </button>
        );
      })}
    </div>
  );
}
