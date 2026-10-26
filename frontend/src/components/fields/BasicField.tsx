import { useRef } from "react";

import type { InputField } from "../../types/api";
import { ui } from "../../utils/ui";
import { FieldWrapper } from "./FieldWrapper";
import { KeypadToggle, MathKeypad } from "./MathKeypad";
import { useKeypadInput } from "./useKeypadInput";

interface BasicFieldProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
  /** Variables the method allows (keypad variable tab). */
  variables?: string[];
}

/** Fallback variable buttons for free-form equation fields. */
const DEFAULT_VARIABLES = ["x", "y", "z"];

/** Text, select and boolean controls. */
export function BasicField({ field, value, onChange, error, variables }: BasicFieldProps) {
  const text = String(value ?? "");
  const keypadVariables = variables && variables.length > 0 ? variables : DEFAULT_VARIABLES;
  const inputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const keypad = useKeypadInput<HTMLInputElement | HTMLTextAreaElement>(
    field.type === "text" && field.rows ? textareaRef : inputRef,
    text,
    (next) => onChange(next),
  );

  if (field.type === "boolean") {
    return (
      <FieldWrapper field={field} error={error}>
        <label className="inline-flex cursor-pointer items-center gap-3 rounded-control border border-line bg-surface px-3.5 py-2.5 text-sm text-ink transition duration-150 hover:border-line-strong">
          <span className="relative inline-flex h-5 w-9 shrink-0 items-center">
            <input
              id={field.key}
              type="checkbox"
              checked={Boolean(value)}
              onChange={(event) => onChange(event.target.checked)}
              className="peer sr-only"
            />
            <span className="h-5 w-9 rounded-pill bg-line-strong transition duration-150 peer-checked:bg-accent-solid peer-focus-visible:ring-2 peer-focus-visible:ring-accent-500 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-canvas" />
            <span className="absolute left-0.5 h-4 w-4 rounded-full bg-surface shadow-sm transition duration-150 peer-checked:translate-x-4" />
          </span>
          Enabled
        </label>
      </FieldWrapper>
    );
  }

  if (field.type === "select") {
    return (
      <FieldWrapper field={field} error={error}>
        <select
          id={field.key}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={Boolean(error)}
          className={`${ui.input} cursor-pointer ${error ? ui.inputError : ""}`}
        >
          {!field.required && <option value="">— select —</option>}
          {field.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </FieldWrapper>
    );
  }

  if (field.type === "text" && field.rows) {
    return (
      <FieldWrapper field={field} error={error}>
        <textarea
          ref={textareaRef}
          id={field.key}
          rows={field.rows}
          value={text}
          placeholder={field.placeholder}
          spellCheck={false}
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

  return (
    <FieldWrapper field={field} error={error}>
      <input
        ref={inputRef}
        id={field.key}
        type="text"
        value={text}
        placeholder={field.placeholder}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={field.help ? `${field.key}-help` : undefined}
        className={`${ui.input} ${error ? ui.inputError : ""}`}
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
