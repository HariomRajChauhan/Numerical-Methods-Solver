import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MethodForm } from "../components/MethodForm";
import { BasicField } from "../components/fields/BasicField";
import { FunctionField } from "../components/fields/FunctionField";
import { ListField } from "../components/fields/ListField";
import { MatrixInput } from "../components/MatrixInput";
import type { InputField, MethodMeta } from "../types/api";
import { normalizeMath } from "../utils/mathNormalize";

function makeField(overrides: Partial<InputField>): InputField {
  return {
    key: "function",
    label: "Function f(x)",
    type: "function",
    required: true,
    default: null,
    help: "",
    placeholder: "",
    min: null,
    max: null,
    variable: "x",
    rows: null,
    cols: null,
    options: [],
    ...overrides,
  };
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("Math keypad (FunctionField)", () => {
  it("is hidden until toggled and inserts a token at the caret", () => {
    const onChange = vi.fn();
    render(<FunctionField field={makeField({})} value="x+1" onChange={onChange} />);

    expect(screen.queryByRole("group", { name: /keypad/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));

    const input = screen.getByLabelText(/Function f\(x\)/) as HTMLInputElement;
    input.setSelectionRange(1, 1);
    fireEvent.click(screen.getByRole("button", { name: "Insert 2" }));
    expect(onChange).toHaveBeenCalledWith("x2+1");
  });

  it("replaces the selected text instead of overwriting the field", () => {
    const onChange = vi.fn();
    render(<FunctionField field={makeField({})} value="ab+1" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));

    const input = screen.getByLabelText(/Function f\(x\)/) as HTMLInputElement;
    input.setSelectionRange(0, 1);
    fireEvent.click(screen.getByRole("button", { name: "Insert 1" }));
    expect(onChange).toHaveBeenCalledWith("1b+1");
  });

  it("inserts function names with an open bracket and switches tabs", () => {
    const onChange = vi.fn();
    render(<FunctionField field={makeField({})} value="" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));

    fireEvent.click(screen.getByRole("tab", { name: "Functions" }));
    fireEvent.click(screen.getByRole("button", { name: "Insert sin" }));
    expect(onChange).toHaveBeenCalledWith("sin(");
  });

  it("clears and hides again", () => {
    const onChange = vi.fn();
    render(<FunctionField field={makeField({})} value="x^2" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("tab", { name: "Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Clear the field" }));
    expect(onChange).toHaveBeenCalledWith("");

    fireEvent.click(screen.getByRole("button", { name: "Hide keypad" }));
    expect(screen.queryByRole("group", { name: /keypad/i })).not.toBeInTheDocument();
  });
});

describe("Keypad visibility persistence", () => {
  beforeEach(() => window.localStorage.clear());

  it("remembers the open state in localStorage", () => {
    const { unmount } = render(
      <FunctionField field={makeField({})} value="" onChange={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    expect(window.localStorage.getItem("nms.keypad.open")).toBe("1");
    unmount();

    render(<FunctionField field={makeField({})} value="" onChange={vi.fn()} />);
    expect(screen.getByRole("group", { name: /keypad/i })).toBeInTheDocument();
  });

  it("defaults to hidden when storage is empty", () => {
    window.localStorage.clear();
    render(<FunctionField field={makeField({})} value="" onChange={vi.fn()} />);
    expect(screen.queryByRole("group", { name: /keypad/i })).not.toBeInTheDocument();
  });
});

describe("Variable filtering", () => {
  it("shows only the field's own variable for a function field", () => {
    render(
      <FunctionField
        field={makeField({ variable: "x" })}
        value=""
        onChange={vi.fn()}
        variables={["x", "y", "z"]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("tab", { name: "Variables" }));
    expect(screen.getByRole("button", { name: "Insert variable x" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Insert variable t" })).not.toBeInTheDocument();
  });

  it("shows every variable of a comma-separated function field", () => {
    render(
      <FunctionField
        field={makeField({ variable: "x, y" })}
        value=""
        onChange={vi.fn()}
        variables={["x", "y", "z"]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("tab", { name: "Variables" }));
    expect(screen.getByRole("button", { name: "Insert variable x" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Insert variable y" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Insert variable z" })).not.toBeInTheDocument();
  });

  it("uses the method variables for equation text fields", () => {
    render(
      <BasicField
        field={makeField({ key: "equations", type: "text", rows: 3, variable: null })}
        value=""
        onChange={vi.fn()}
        variables={["x", "t"]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("tab", { name: "Variables" }));
    expect(screen.getByRole("button", { name: "Insert variable x" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Insert variable t" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Insert variable y" })).not.toBeInTheDocument();
  });

  it("falls back to x/y/z for a free-form text field with no schema variables", () => {
    render(
      <BasicField
        field={makeField({ key: "equations", type: "text", rows: 3, variable: null })}
        value=""
        onChange={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("tab", { name: "Variables" }));
    expect(screen.getByRole("button", { name: "Insert variable y" })).toBeInTheDocument();
  });
});

describe("MethodForm variable wiring", () => {
  const META: MethodMeta = {
    id: "nonlinear_system_direct",
    chapter: "ch1_nonlinear",
    variables: ["x", "y", "z"],
    name: "Non-linear Systems",
    status: "available",
    summary: "",
    theory: "",
    pseudocode: "",
    formulas: [],
    chapter_title: "Non-linear Equations",
    chapter_number: 1,
    examples: [],
    input_schema: [
      {
        key: "equations",
        label: "Iteration equations",
        type: "text",
        required: true,
        default: null,
        help: "",
        placeholder: "",
        min: null,
        max: null,
        variable: null,
        rows: 3,
        cols: null,
        options: [],
      },
    ],
  };

  it("passes the method variables to equation fields", () => {
    render(
      <MethodForm
        meta={META}
        inputs={{ equations: "" }}
        status="idle"
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onClear={vi.fn()}
        onLoadExample={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("tab", { name: "Variables" }));
    expect(screen.getByRole("button", { name: "Insert variable z" })).toBeInTheDocument();
  });
});

describe("Compact numeric keypad", () => {
  it("inserts digits into a vector via ListField", () => {
    const onChange = vi.fn();
    render(
      <ListField
        field={makeField({ key: "guess", type: "vector", variable: null })}
        value=""
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("button", { name: "Insert 7" }));
    expect(onChange).toHaveBeenCalledWith("7");
  });

  it("edits the focused matrix cell and navigates with the arrow keys", () => {
    const onChange = vi.fn();
    render(
      <MatrixInput
        field={makeField({ key: "matrix", type: "matrix", rows: 2, cols: 2 })}
        value={[
          ["", ""],
          ["", ""],
        ]}
        onChange={onChange}
      />,
    );

    const cell = screen.getByLabelText(/row 1 column 1/);
    fireEvent.focus(cell);

    fireEvent.click(screen.getByRole("button", { name: "Keypad" }));
    fireEvent.click(screen.getByRole("button", { name: "Insert 5" }));
    expect(onChange).toHaveBeenCalledWith([
      ["5", ""],
      ["", ""],
    ]);

    fireEvent.keyDown(cell, { key: "ArrowRight" });
    expect(screen.getByLabelText(/row 1 column 2/)).toHaveFocus();
  });
});

describe("normalizeMath", () => {
  it("folds unicode operators and symbols", () => {
    expect(normalizeMath("4\u2212x\u00b2")).toBe("4-x^2");
    expect(normalizeMath("2\u00d7\u03c0")).toBe("2*pi");
    expect(normalizeMath("6\u00f72")).toBe("6/2");
    expect(normalizeMath("\u221a(4-x)")).toBe("sqrt(4-x)");
  });

  it("folds superscript runs and leaves ASCII untouched", () => {
    expect(normalizeMath("x\u00b2\u00b3")).toBe("x^23");
    expect(normalizeMath("x^2 + 2*x")).toBe("x^2 + 2*x");
  });
});
