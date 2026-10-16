import type { ReactNode } from "react";

import type { InputField } from "../../types/api";
import { ui } from "../../utils/ui";

interface FieldWrapperProps {
  field: InputField;
  error?: string;
  children: ReactNode;
  /** Extra element shown right below the control (e.g. a live preview). */
  preview?: ReactNode;
}

/** Shared label / help / error chrome for every input field. */
export function FieldWrapper({ field, error, children, preview }: FieldWrapperProps) {
  const helpId = `${field.key}-help`;
  const errorId = `${field.key}-error`;
  return (
    <div>
      <label htmlFor={field.key} className={ui.label}>
        {field.label}
        {field.required && (
          <span aria-hidden="true" className="ml-0.5 text-rose-500">
            *
          </span>
        )}
      </label>
      <div className="mt-1.5">{children}</div>
      {field.help && (
        <p id={helpId} className={ui.help}>
          {field.help}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className={ui.error}>
          {error}
        </p>
      )}
      {preview}
    </div>
  );
}
