import type { InputField } from "../../types/api";
import { ui } from "../../utils/ui";
import { FieldWrapper } from "./FieldWrapper";

interface BasicFieldProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

/** Text, select and boolean controls. */
export function BasicField({ field, value, onChange, error }: BasicFieldProps) {
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

  return (
    <FieldWrapper field={field} error={error}>
      <input
        id={field.key}
        type="text"
        value={String(value ?? "")}
        placeholder={field.placeholder}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={field.help ? `${field.key}-help` : undefined}
        className={`${ui.input} ${error ? ui.inputError : ""}`}
      />
    </FieldWrapper>
  );
}
