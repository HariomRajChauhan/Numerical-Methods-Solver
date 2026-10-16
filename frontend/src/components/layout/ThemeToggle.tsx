import { useThemeStore } from "../../store/theme";
import { ui } from "../../utils/ui";

const MODES = [
  { id: "light", label: "Light", icon: "☀" },
  { id: "dark", label: "Dark", icon: "☾" },
  { id: "system", label: "System", icon: "⌘" },
] as const;

/** Light / dark / system switch (class-based Tailwind dark mode). */
export function ThemeToggle() {
  const mode = useThemeStore((state) => state.mode);
  const setMode = useThemeStore((state) => state.setMode);

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className="inline-flex rounded-lg border border-slate-300 p-0.5 dark:border-slate-700"
    >
      {MODES.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => setMode(option.id)}
          aria-pressed={mode === option.id}
          title={`${option.label} theme`}
          className={`rounded-md px-2 py-1 text-xs font-medium transition ${
            mode === option.id
              ? "bg-indigo-600 text-white"
              : `${ui.btnGhost} !px-2`
          }`}
        >
          <span aria-hidden="true">{option.icon}</span>
          <span className="sr-only">{option.label} theme</span>
        </button>
      ))}
    </div>
  );
}
