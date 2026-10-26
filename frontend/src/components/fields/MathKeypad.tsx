import { useState } from "react";

import { ui } from "../../utils/ui";
import type { KeypadAction } from "./useKeypadInput";

interface MathKeypadProps {
  /** Variables the current method allows (e.g. ["x"] or ["x", "y", "z"]). */
  variables?: string[];
  onAction: (action: KeypadAction) => void;
}

type TabId = "numbers" | "operators" | "functions" | "variables" | "edit";

const TABS: { id: TabId; label: string }[] = [
  { id: "numbers", label: "Numbers" },
  { id: "operators", label: "Operators" },
  { id: "functions", label: "Functions" },
  { id: "variables", label: "Variables" },
  { id: "edit", label: "Edit" },
];

const NUMBERS = ["7", "8", "9", "4", "5", "6", "1", "2", "3", "0", ".", "e", "pi"];
const OPERATORS = ["+", "-", "*", "/", "^", "(", ")", ","];
const FUNCTIONS = [
  "sqrt",
  "abs",
  "sin",
  "cos",
  "tan",
  "asin",
  "acos",
  "atan",
  "exp",
  "ln",
  "log",
  "sinh",
  "cosh",
  "tanh",
];

const BUTTON_BASE =
  "inline-flex h-10 min-w-10 items-center justify-center rounded-lg border border-slate-200 " +
  "bg-white px-2 font-mono text-sm text-slate-700 shadow-sm transition active:scale-95 " +
  "hover:border-indigo-300 hover:bg-indigo-50/60 hover:text-indigo-700 " +
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 " +
  "dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-slate-200 dark:hover:border-indigo-400/40 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-200";

interface KeypadButtonProps {
  label: string;
  ariaLabel: string;
  onClick: () => void;
  wide?: boolean;
}

function KeypadButton({ label, ariaLabel, onClick, wide }: KeypadButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      title={ariaLabel}
      onClick={onClick}
      className={`${BUTTON_BASE} ${wide ? "min-w-[4.5rem] px-3" : "min-w-10"}`}
    >
      {label}
    </button>
  );
}

/** A toggleable, tabbed on-screen keypad for building mathematical expressions. */
export function MathKeypad({ variables = [], onAction }: MathKeypadProps) {
  const [tab, setTab] = useState<TabId>("numbers");

  return (
    <div
      role="group"
      aria-label="Mathematical keypad"
      className="mt-2 max-w-full overflow-hidden rounded-xl border border-slate-200/80 bg-slate-50/80 p-2 dark:border-white/[0.08] dark:bg-white/[0.02]"
    >
      <div
        role="tablist"
        aria-label="Keypad sections"
        className="no-scrollbar mb-2 flex gap-1 overflow-x-auto"
      >
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            aria-controls={`keypad-panel-${item.id}`}
            onClick={() => setTab(item.id)}
            className={`shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
              tab === item.id
                ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/25"
                : "text-slate-600 hover:bg-white hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-slate-100"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        aria-label={TABS.find((entry) => entry.id === tab)?.label}
        className="flex flex-wrap gap-1.5"
      >
        {tab === "numbers" &&
          NUMBERS.map((key) => (
            <KeypadButton
              key={key}
              label={key}
              ariaLabel={`Insert ${key}`}
              onClick={() => onAction({ type: "insert", text: key })}
            />
          ))}

        {tab === "operators" && (
          <>
            {OPERATORS.map((key) => (
              <KeypadButton
                key={key}
                label={key}
                ariaLabel={`Insert ${key}`}
                onClick={() => onAction({ type: "insert", text: key })}
              />
            ))}
            <KeypadButton
              label="x²"
              ariaLabel="Insert squared"
              wide
              onClick={() => onAction({ type: "insert", text: "^2" })}
            />
            <KeypadButton
              label="xⁿ"
              ariaLabel="Insert power"
              wide
              onClick={() => onAction({ type: "insert", text: "^(" })}
            />
          </>
        )}

        {tab === "functions" &&
          FUNCTIONS.map((name) => (
            <KeypadButton
              key={name}
              label={`${name}(`}
              ariaLabel={`Insert ${name}`}
              wide
              onClick={() => onAction({ type: "insert", text: `${name}(` })}
            />
          ))}

        {tab === "variables" &&
          (variables.length > 0 ? (
            variables.map((name) => (
              <KeypadButton
                key={name}
                label={name}
                ariaLabel={`Insert variable ${name}`}
                onClick={() => onAction({ type: "insert", text: name })}
              />
            ))
          ) : (
            <p className="px-1 py-2 text-xs text-slate-600 dark:text-slate-400">
              No variables for this field.
            </p>
          ))}

        {tab === "edit" && (
          <>
            <KeypadButton
              label="\u232b"
              ariaLabel="Backspace"
              wide
              onClick={() => onAction({ type: "backspace" })}
            />
            <KeypadButton
              label="Clear"
              ariaLabel="Clear the field"
              wide
              onClick={() => onAction({ type: "clear" })}
            />
            <KeypadButton
              label="\u2190"
              ariaLabel="Move cursor left"
              wide
              onClick={() => onAction({ type: "left" })}
            />
            <KeypadButton
              label="\u2192"
              ariaLabel="Move cursor right"
              wide
              onClick={() => onAction({ type: "right" })}
            />
          </>
        )}
      </div>
    </div>
  );
}

interface KeypadToggleProps {
  open: boolean;
  onToggle: () => void;
}

/** Show/hide button for the keypad (state is shared across all fields). */
export function KeypadToggle({ open, onToggle }: KeypadToggleProps) {
  return (
    <button type="button" onClick={onToggle} aria-expanded={open} className={ui.btnGhost}>
      {open ? "Hide keypad" : "Keypad"}
    </button>
  );
}
