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
import { Icon } from "./ui/Icon";

interface MethodFormProps {
  meta: MethodMeta;
  inputs: Record<string, unknown>;
  status: "idle" | "loading" | "error" | "done";
  error?: ApiError;
  onChange: (key: string, value: unknown) => void;
  onSubmit: () => void;
  onClear: () => void;
  onLoadExample: (inputs: MethodExample["inputs"]) => void;
  /** Let a sticky workspace toolbar own the primary action. */
  showSubmit?: boolean;
  /** Lets a toolbar submit button target this form with the `form` attribute. */
  formId?: string;
}

/**
 * The variables a method allows, read from its schema: the explicit
 * `meta.variables` list first, otherwise every `variable` named by its fields.
 * Free-form declaration fields (an independent variable and a list of state
 * variables, as used by the ODE-system methods) are folded in from the current
 * inputs so the keypad always offers the names the student declared.
 */
function methodVariables(meta: MethodMeta, inputs: Record<string, unknown>): string[] {
  const declared: string[] = [];
  const independent = inputs.independent_variable;
  if (typeof independent === "string" && independent.trim()) {
    declared.push(independent.trim());
  }
  const state = inputs.state_variables;
  if (typeof state === "string") {
    declared.push(...state.split(/[,\s]+/).filter(Boolean));
  }
  if (declared.length > 0) {
    return meta.variables && meta.variables.length > 0
      ? Array.from(new Set([...meta.variables, ...declared]))
      : Array.from(new Set(declared));
  }
  if (meta.variables && meta.variables.length > 0) return meta.variables;
  const fromFields = meta.input_schema
    .map((field) => field.variable)
    .filter((name): name is string => Boolean(name));
  return Array.from(new Set(fromFields));
}

function renderField(
  field: InputField,
  value: unknown,
  onChange: (value: unknown) => void,
  variables: string[],
): ReactElement {
  switch (field.type) {
    case "function":
      return <FunctionField field={field} value={value} onChange={onChange} variables={variables} />;
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
      return <BasicField field={field} value={value} onChange={onChange} variables={variables} />;
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
  showSubmit = true,
  formId = "method-form",
}: MethodFormProps) {
  const busy = status === "loading";
  const variables = methodVariables(meta, inputs);

  return (
    <form
      id={formId}
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy) onSubmit();
      }}
      onKeyDown={(event) => {
        if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
          event.preventDefault();
          if (!busy) onSubmit();
        }
      }}
      className="space-y-5"
    >
      {error && <ErrorAlert error={error} />}

      {meta.examples.length > 0 && (
        <div className={`${ui.surface} p-3`}>
          <label htmlFor="example-select" className={ui.label}>
            <span className="flex items-center gap-1.5">
              <Icon name="sparkles" size={13} className="text-accent-text" />
              Worked examples
            </span>
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
          <p className="mt-1.5 text-2xs leading-relaxed text-ink-muted">
            Loads a ready-made problem so you can see the full solution immediately.
          </p>
        </div>
      )}

      {meta.input_schema.map((field) => (
        <div key={field.key}>
          {renderField(field, inputs[field.key], (value) => onChange(field.key, value), variables)}
        </div>
      ))}

      <div
        className={`flex flex-wrap gap-2 border-t border-line pt-4 ${
          showSubmit ? "" : "justify-end"
        }`}
      >
        {showSubmit && (
          <button
            type="submit"
            disabled={busy}
            aria-busy={busy}
            className={`${ui.btnPrimary} min-w-[8rem] flex-1`}
          >
            <Icon
              name={busy ? "loader" : "play"}
              size={15}
              className={busy ? "animate-spin" : undefined}
            />
            {busy ? "Solving…" : "Solve"}
          </button>
        )}
        <button type="button" onClick={onClear} disabled={busy} className={ui.btn}>
          <Icon name="refresh" size={14} />
          Clear result
        </button>
      </div>
    </form>
  );
}
