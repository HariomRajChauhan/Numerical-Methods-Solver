import { type ReactElement } from "react";

import { ApiError } from "../api/client";
import type { InputField, MethodExample, MethodMeta } from "../types/api";
import { ui } from "../utils/ui";
import { ErrorAlert } from "./ErrorAlert";
import { BasicField } from "./fields/BasicField";
import { FunctionField } from "./fields/FunctionField";
import { ListField } from "./fields/ListField";
import { ScalarField } from "./fields/ScalarField";
import { MatrixInput } from "./MatrixInput";

interface MethodFormProps {
  meta: MethodMeta;
  inputs: Record<string, unknown>;
  status: "idle" | "loading" | "error" | "done";
  error?: ApiError;
  onChange: (key: string, value: unknown) => void;
  onSubmit: () => void;
  onClear: () => void;
  onLoadExample: (inputs: MethodExample["inputs"]) => void;
}

function renderField(
  field: InputField,
  value: unknown,
  onChange: (value: unknown) => void,
): ReactElement {
  switch (field.type) {
    case "function":
      return <FunctionField field={field} value={value} onChange={onChange} />;
    case "matrix":
      return <MatrixInput field={field} value={value} onChange={onChange} />;
    case "vector":
    case "data_points":
      return <ListField field={field} value={value} onChange={onChange} />;
    case "number":
    case "integer":
    case "tolerance":
    case "max_iterations":
    case "precision":
      return <ScalarField field={field} value={value} onChange={onChange} />;
    case "text":
    case "select":
    case "boolean":
    default:
      return <BasicField field={field} value={value} onChange={onChange} />;
  }
}

/**
 * Auto-generated input form: one control per schema field.
 * Adding a backend method needs NO change here — the schema drives everything.
 */
export function MethodForm({
  meta,
  inputs,
  status,
  error,
  onChange,
  onSubmit,
  onClear,
  onLoadExample,
}: MethodFormProps) {
  const busy = status === "loading";

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      className="space-y-5"
    >
      {error && <ErrorAlert error={error} />}

      {meta.examples.length > 0 && (
        <div>
          <label htmlFor="example-select" className={ui.label}>
            Load an example
          </label>
          <select
            id="example-select"
            value=""
            onChange={(event) => {
              const example = meta.examples.find((item) => item.name === event.target.value);
              if (example) onLoadExample(example.inputs);
            }}
            className={`${ui.input} mt-1.5`}
          >
            <option value="">— choose a worked example —</option>
            {meta.examples.map((example) => (
              <option key={example.name} value={example.name}>
                {example.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {meta.input_schema.map((field) => (
        <div key={field.key}>
          {renderField(field, inputs[field.key], (value) => onChange(field.key, value))}
        </div>
      ))}

      <div className="flex flex-wrap gap-2 pt-1">
        <button type="submit" disabled={busy} className={ui.btnPrimary}>
          {busy ? "Solving…" : "Solve"}
        </button>
        <button type="button" onClick={onClear} disabled={busy} className={ui.btn}>
          Clear result
        </button>
      </div>
    </form>
  );
}
