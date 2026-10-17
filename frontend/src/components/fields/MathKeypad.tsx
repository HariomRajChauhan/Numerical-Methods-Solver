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
  "inline-flex h-11 min-w-11 items-center justify-center rounded-lg border border-slate-300 " +
  "bg-white px-2 font-mono text-base text-slate-800 shadow-sm transition active:scale-95 " +
  "hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 " +
  "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800";

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
      className={`${BUTTON_BASE} ${wide ? "min-w-[4.5rem] px-3" : "min-w-11"}`}
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
      className="mt-2 max-w-full overflow-hidden rounded-lg border border-slate-200 bg-slate-50 p-2 dark:border-slate-800 dark:bg-slate-950/40"
    >
      <div
        role="tablist"
        aria-label="Keypad sections"
        className="mb-2 flex flex-wrap gap-1 overflow-x-auto"
      >
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            aria-controls={`keypad-panel-${item.id}`}
            onClick={() => setTab(item.id)}
            className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
              tab === item.id
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"
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
            <p className="px-1 py-2 text-xs text-slate-500 dark:text-slate-400">
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
