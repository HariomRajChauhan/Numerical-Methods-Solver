import { useMemo, useRef } from "react";
import { parse } from "mathjs";

import type { InputField } from "../../types/api";
import { normalizeMath } from "../../utils/mathNormalize";
import { ui } from "../../utils/ui";
import { LatexView } from "../LatexView";
import { FieldWrapper } from "./FieldWrapper";
import { KeypadToggle, MathKeypad } from "./MathKeypad";
import { useKeypadInput } from "./useKeypadInput";

interface FunctionFieldProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
  /** Variables the method allows (used when the field has no single variable). */
  variables?: string[];
}

/**
 * Expression input with a live KaTeX preview and an optional on-screen keypad.
 * mathjs is used ONLY for client-side preview/validation; the backend parser
 * remains the single source of truth for what is accepted.
 */
export function FunctionField({ field, value, onChange, error, variables }: FunctionFieldProps) {
  const text = String(value ?? "");
  const variable = field.variable ?? "x";
  const keypadVariables = field.variable ? [field.variable] : (variables ?? []);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const keypad = useKeypadInput(inputRef, text, (next) => onChange(next));

  const preview = useMemo(() => {
    if (!text.trim()) return { latex: "", error: null as string | null };
    try {
      const node = parse(normalizeMath(text));
      return { latex: node.toTex({ parenthesis: "keep", implicit: "hide" }), error: null };
    } catch (parseError) {
      return { latex: "", error: (parseError as Error).message };
    }
  }, [text]);

  return (
    <FieldWrapper
      field={field}
      error={error}
      preview={
        <div className="mt-2 min-h-[1.5rem]">
          {preview.latex && (
            <div className="overflow-x-auto rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950/60">
              <LatexView latex={preview.latex} />
            </div>
          )}
          {preview.error && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Preview unavailable: {preview.error} (the solver will validate it too)
            </p>
          )}
        </div>
      }
    >
      <input
        ref={inputRef}
        id={field.key}
        type="text"
        spellCheck={false}
        autoComplete="off"
        value={text}
        placeholder={field.placeholder || `e.g. ${variable}^3 - ${variable} - 1`}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={field.help ? `${field.key}-help` : undefined}
        className={`${ui.input} font-mono ${error ? ui.inputError : ""}`}
      />
      <div className="mt-1">
        <KeypadToggle open={keypad.show} onToggle={keypad.toggle} />
      </div>
      {keypad.show && (
        <MathKeypad variables={keypadVariables} onAction={keypad.handleAction} />
      )}
    </FieldWrapper>
  );
}
