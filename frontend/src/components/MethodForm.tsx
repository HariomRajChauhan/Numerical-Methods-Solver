import { type ReactElement, useState } from "react";

import { ApiError } from "../api/client";
import type { InputField, MethodExample, MethodMeta } from "../types/api";
import { ui } from "../utils/ui";
import { validateInputs } from "../utils/validation";
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
  error?: string,
): ReactElement {
  switch (field.type) {
    case "function":
      return (
        <FunctionField
          field={field}
          value={value}
          onChange={onChange}
          variables={variables}
          error={error}
        />
      );
    case "matrix":
      return <MatrixInput field={field} value={value} onChange={onChange} error={error} />;
    case "vector":
    case "data_points":
      return <ListField field={field} value={value} onChange={onChange} error={error} />;
    case "number":
    case "integer":
    case "tolerance":
    case "max_iterations":
    case "precision":
      return <ScalarField field={field} value={value} onChange={onChange} error={error} />;
    case "text":
    case "select":
    case "boolean":
    default:
      return (
        <BasicField
          field={field}
          value={value}
          onChange={onChange}
          variables={variables}
          error={error}
        />
      );
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
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const errorCount = Object.keys(fieldErrors).length;

  function clearFieldError(key: string): void {
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function handleChange(key: string, value: unknown): void {
    onChange(key, value);
    clearFieldError(key);
  }

  function handleLoadExample(exampleInputs: MethodExample["inputs"]): void {
    setFieldErrors({});
    onLoadExample(exampleInputs);
  }

  function handleClear(): void {
    setFieldErrors({});
    onClear();
  }

  function submit(): void {
    if (busy) return;
    const next = validateInputs(meta, inputs);
    setFieldErrors(next);
    if (Object.keys(next).length > 0) {
      const firstKey = meta.input_schema.find((field) => next[field.key])?.key;
      if (!firstKey) return;
      const field = document.getElementById(`field-${firstKey}`);
      field?.scrollIntoView?.({ block: "center" });
      field?.querySelector<HTMLElement>("input, textarea, select, button")?.focus();
      return;
    }
    onSubmit();
  }

  return (
    <form
      id={formId}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      onKeyDown={(event) => {
        if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
          event.preventDefault();
          submit();
        }
      }}
      className="space-y-5"
    >
      {error && <ErrorAlert error={error} />}

      {errorCount > 0 && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-panel border border-danger/20 bg-danger-soft px-3.5 py-3 text-xs text-ink-muted"
        >
          <Icon name="alert" size={15} className="mt-0.5 shrink-0 text-danger" />
          <p>
            <span className="font-semibold text-ink">
              Fix {errorCount} highlighted field{errorCount === 1 ? "" : "s"}.
            </span>{" "}
            The solver needs valid inputs before it can run.
          </p>
        </div>
      )}

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
              if (example) handleLoadExample(example.inputs);
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
        <div key={field.key} id={`field-${field.key}`}>
          {renderField(
            field,
            inputs[field.key],
            (value) => handleChange(field.key, value),
            variables,
            fieldErrors[field.key],
          )}
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
            aria-keyshortcuts="Control+Enter Meta+Enter"
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
        <button type="button" onClick={handleClear} disabled={busy} className={ui.btn}>
          <Icon name="refresh" size={14} />
          Clear result
        </button>
      </div>
    </form>
  );
}
