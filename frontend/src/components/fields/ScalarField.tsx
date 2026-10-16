import type { InputField } from "../../types/api";
import { ui } from "../../utils/ui";
import { FieldWrapper } from "./FieldWrapper";

interface ScalarFieldProps {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
}

const INTEGER_TYPES = new Set(["integer", "max_iterations", "precision"]);

/** Numeric input (number, integer, tolerance, max_iterations, precision). */
export function ScalarField({ field, value, onChange, error }: ScalarFieldProps) {
  const isInteger = INTEGER_TYPES.has(field.type);
  const isTolerance = field.type === "tolerance";

  return (
    <FieldWrapper field={field} error={error}>
      <input
        id={field.key}
        type="number"
        inputMode={isInteger || isTolerance ? "numeric" : "decimal"}
        step={field.placeholder || (isInteger ? 1 : isTolerance ? 1e-6 : "any")}
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={field.help ? `${field.key}-help` : undefined}
        className={`${ui.input} font-mono ${error ? ui.inputError : ""}`}
      />
    </FieldWrapper>
  );
}
