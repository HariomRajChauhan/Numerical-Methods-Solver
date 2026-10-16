import type { InputField } from "../../types/api";
import { ui } from "../../utils/ui";
import { FieldWrapper } from "./FieldWrapper";

interface ListFieldProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

function parseNumbers(text: string): number[] {
  return text
    .split(/[,\s;]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map(Number);
}

function parsePoints(text: string): Array<[number, number]> {
  return text
    .split(/[;\n]+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => chunk.split(/[,\s]+/).map(Number))
    .filter((parts) => parts.length === 2 && parts.every((n) => Number.isFinite(n)))
    .map((parts) => [parts[0], parts[1]] as [number, number]);
}

/** Comma / whitespace separated numbers, or "x,y" point pairs. */
export function ListField({ field, value, onChange, error }: ListFieldProps) {
  const isPoints = field.type === "data_points";
  const text = String(value ?? "");
  const preview = isPoints ? parsePoints(text) : parseNumbers(text);

  return (
    <FieldWrapper
      field={field}
      error={error}
      preview={
        text.trim() && preview.length > 0 ? (
          <p className="mt-1.5 text-xs text-emerald-600 dark:text-emerald-400">
            ✓ {preview.length} {isPoints ? "point(s)" : "value(s)"} detected
          </p>
        ) : null
      }
    >
      {isPoints ? (
        <textarea
          id={field.key}
          rows={4}
          spellCheck={false}
          value={text}
          placeholder={field.placeholder || "0,1; 1,2; 2,5"}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={Boolean(error)}
          className={`${ui.input} font-mono ${error ? ui.inputError : ""}`}
        />
      ) : (
        <input
          id={field.key}
          type="text"
          spellCheck={false}
          value={text}
          placeholder={field.placeholder || "1, 2, 3"}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={Boolean(error)}
          className={`${ui.input} font-mono ${error ? ui.inputError : ""}`}
        />
      )}
    </FieldWrapper>
  );
}
