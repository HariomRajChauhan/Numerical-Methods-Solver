import { useEffect, useRef, useState } from "react";

import type { InputField } from "../../types/api";
import { normalizeMath } from "../../utils/mathNormalize";
import { ui } from "../../utils/ui";
import { LatexView } from "../LatexView";
import { Icon } from "../ui/Icon";
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
  // ``variable`` may list several names separated by commas (e.g. "x, y" for an
  // ODE right-hand side); a single name is the common case.
  const fieldVariables = field.variable
    ? field.variable.split(/[,\s]+/).filter(Boolean)
    : [];
  const variable = fieldVariables[0] ?? "x";
  const keypadVariables = fieldVariables.length > 0 ? fieldVariables : (variables ?? []);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const keypad = useKeypadInput(inputRef, text, (next) => onChange(next));

  const [renderState, setRenderState] = useState<{
    text: string;
    latex: string;
    error: string | null;
  }>({ text: "", latex: "", error: null });

  useEffect(() => {
    if (!text.trim()) return;
    let active = true;
    void import("mathjs")
      .then(({ parse }) => {
        if (!active) return;
        try {
          const node = parse(normalizeMath(text));
          setRenderState({
            text,
            latex: node.toTex({ parenthesis: "keep", implicit: "hide" }),
            error: null,
          });
        } catch (parseError) {
          setRenderState({ text, latex: "", error: (parseError as Error).message });
        }
      })
      .catch((loadError: unknown) => {
        if (active) {
          setRenderState({
            text,
            latex: "",
            error:
              loadError instanceof Error ? loadError.message : "Preview engine unavailable.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [text]);

  const preview =
    text.trim() && renderState.text === text
      ? { latex: renderState.latex, error: renderState.error }
      : { latex: "", error: null };

  return (
    <FieldWrapper
      field={field}
      error={error}
      preview={
        <div className="mt-2 min-h-[1.75rem]">
          {preview.latex && (
            <div className="flex items-start gap-2 overflow-x-auto rounded-control border border-line bg-surface-muted px-3 py-2">
              <span className="mt-0.5 shrink-0 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">
                Preview
              </span>
              <LatexView latex={preview.latex} />
            </div>
          )}
          {preview.error && (
            <p className="flex items-start gap-1.5 text-xs text-warning">
              <Icon name="alert" size={13} className="mt-0.5 shrink-0" />
              <span>
                Preview unavailable: {preview.error} (the solver will validate it too)
              </span>
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
