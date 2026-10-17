import type { KeypadAction } from "./useKeypadInput";

interface NumericKeypadProps {
  onAction: (action: KeypadAction) => void;
  /** Label the group for assistive tech (e.g. "Numeric keypad"). */
  label?: string;
}

const BUTTON =
  "inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-300 bg-white " +
  "font-mono text-base text-slate-800 shadow-sm transition active:scale-95 hover:bg-slate-100 " +
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 " +
  "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800";

interface Key {
  label: string;
  ariaLabel: string;
  action: KeypadAction;
}

const KEYS: Key[] = [
  { label: "7", ariaLabel: "Insert 7", action: { type: "insert", text: "7" } },
  { label: "8", ariaLabel: "Insert 8", action: { type: "insert", text: "8" } },
  { label: "9", ariaLabel: "Insert 9", action: { type: "insert", text: "9" } },
  { label: "/", ariaLabel: "Insert divide", action: { type: "insert", text: "/" } },
  { label: "4", ariaLabel: "Insert 4", action: { type: "insert", text: "4" } },
  { label: "5", ariaLabel: "Insert 5", action: { type: "insert", text: "5" } },
  { label: "6", ariaLabel: "Insert 6", action: { type: "insert", text: "6" } },
  { label: "-", ariaLabel: "Insert minus", action: { type: "insert", text: "-" } },
  { label: "1", ariaLabel: "Insert 1", action: { type: "insert", text: "1" } },
  { label: "2", ariaLabel: "Insert 2", action: { type: "insert", text: "2" } },
  { label: "3", ariaLabel: "Insert 3", action: { type: "insert", text: "3" } },
  { label: ".", ariaLabel: "Insert decimal point", action: { type: "insert", text: "." } },
  { label: "0", ariaLabel: "Insert 0", action: { type: "insert", text: "0" } },
  { label: "Back", ariaLabel: "Backspace", action: { type: "backspace" } },
];

/** Compact numeric keypad shared by vector and matrix inputs. */
export function NumericKeypad({ onAction, label = "Numeric keypad" }: NumericKeypadProps) {
  return (
    <div
      role="group"
      aria-label={label}
      className="mt-1.5 inline-grid grid-cols-4 gap-1 rounded-lg border border-slate-200 bg-slate-50 p-2 dark:border-slate-800 dark:bg-slate-950/40"
    >
      {KEYS.map((key) => (
        <button
          key={key.label}
          type="button"
          aria-label={key.ariaLabel}
          title={key.ariaLabel}
          className={BUTTON}
          onClick={() => onAction(key.action)}
        >
          {key.label}
        </button>
      ))}
    </div>
  );
}
