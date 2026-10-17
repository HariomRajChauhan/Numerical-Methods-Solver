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
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input
            id={field.key}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => onChange(event.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-600"
          />
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
          className={`${ui.input} ${error ? ui.inputError : ""}`}
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
