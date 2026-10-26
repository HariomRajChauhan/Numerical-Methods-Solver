import { useThemeStore } from "../../store/theme";
import { Icon, type IconName } from "../ui/Icon";

const MODES: { id: "light" | "dark" | "system"; label: string; icon: IconName }[] = [
  { id: "light", label: "Light", icon: "sun" },
  { id: "dark", label: "Dark", icon: "moon" },
  { id: "system", label: "System", icon: "monitor" },
];

/** Light / dark / system switch (class-based Tailwind dark mode). */
export function ThemeToggle() {
  const mode = useThemeStore((state) => state.mode);
  const setMode = useThemeStore((state) => state.setMode);

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className="inline-flex shrink-0 items-center gap-0.5 rounded-xl border border-slate-200 bg-slate-100/70 p-0.5 dark:border-white/[0.08] dark:bg-white/[0.04]"
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
            className={`flex h-7 w-7 items-center justify-center rounded-lg transition sm:h-8 sm:w-8 ${
              active
                ? "bg-white text-indigo-600 shadow-sm dark:bg-slate-700/80 dark:text-indigo-300"
                : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Icon name={option.icon} size={15} />
            <span className="sr-only">{option.label} theme</span>
          </button>
        );
      })}
    </div>
  );
}
