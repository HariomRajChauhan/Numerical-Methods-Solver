import { useRef } from "react";

import type { InputField } from "../../types/api";
import { ui } from "../../utils/ui";
import { Icon } from "../ui/Icon";
import { FieldWrapper } from "./FieldWrapper";
import { KeypadToggle } from "./MathKeypad";
import { NumericKeypad } from "./NumericKeypad";
import { NUMERIC_KEYPAD_STORAGE_KEY, useKeypadInput } from "./useKeypadInput";

interface ListFieldProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

function parseNumbers(text: string): number[] {
  return text
    .split(/[,\s;]+/)
    .filter((part) => part.length > 0)
    .map(Number);
}

function parsePoints(text: string): [number, number][] {
  return text
    .split(/[;\n]+/)
    .map((chunk) => chunk.trim())
    .filter((chunk) => chunk.length > 0)
    .map((chunk) => chunk.split(/[,\s]+/).filter((part) => part.length > 0))
    .filter((parts) => parts.length === 2)
    .map((parts) => [Number(parts[0]), Number(parts[1])] as [number, number]);
}

/** Comma / whitespace separated numbers, or "x,y" point pairs. */
export function ListField({ field, value, onChange, error }: ListFieldProps) {
  const isPoints = field.type === "data_points";
  const text = String(value ?? "");
  const preview = isPoints ? parsePoints(text) : parseNumbers(text);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const keypad = useKeypadInput<HTMLInputElement | HTMLTextAreaElement>(
    isPoints ? textareaRef : inputRef,
    text,
    (next) => onChange(next),
    NUMERIC_KEYPAD_STORAGE_KEY,
  );

  return (
    <FieldWrapper
      field={field}
      error={error}
      preview={
        text.trim() && preview.length > 0 ? (
          <p className="mt-1.5 flex items-center gap-1 text-xs font-medium text-success">
            <Icon name="check" size={13} />
            {preview.length} {isPoints ? "point(s)" : "value(s)"} detected
          </p>
        ) : null
      }
    >
      {isPoints ? (
        <textarea
          ref={textareaRef}
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
          ref={inputRef}
          id={field.key}
          type="text"
          inputMode="decimal"
          spellCheck={false}
          value={text}
          placeholder={field.placeholder || "1, 2, 3"}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={Boolean(error)}
          className={`${ui.input} font-mono ${error ? ui.inputError : ""}`}
        />
      )}
      <div className="mt-1">
        <KeypadToggle open={keypad.show} onToggle={keypad.toggle} />
      </div>
      {keypad.show && <NumericKeypad onAction={keypad.handleAction} />}
    </FieldWrapper>
  );
}
