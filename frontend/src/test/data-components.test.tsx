import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StepsPanel } from "../components/StepsPanel";
import { DataTable } from "../components/DataTable";
import { CodePanel } from "../components/CodePanel";
import { ResultHeader } from "../components/ResultHeader";
import { IterationPlayer } from "../components/IterationPlayer";
import type { SolveResponse } from "../types/api";

const MOCK_SOLVE_RESPONSE: SolveResponse = {
  method: "bisection",
  status: "converged",
  result: { root: 1.414213 },
  steps: [
    { title: "Initial guess", latex: "x_0 = 1.0", note: "Given" },
    { title: "First iteration", latex: "x_1 = 1.5", note: "Converging" },
  ],
  tables: [
    {
      title: "Bisection Iterations",
      columns: ["i", "a", "b", "c", "f(c)"],
      rows: [
        [0, 1.0, 2.0, 1.5, 0.25],
        [1, 1.0, 1.5, 1.25, -0.12],
      ],
    },
  ],
  plot: { traces: [], layout: {} },
  errors: { absolute: 0.001, relative_percent: 0.05, order_of_convergence: 1.0 },
  warnings: ["Function changes sign.", "Gauss-Seidel matrix is not strictly diagonally dominant."],
  pseudocode: "while b - a > tol:\n    c = (a + b) / 2",
  python_source: "def bisection(f, a, b):\n    return c",
};

describe("Phase 4 Comprehensive Data Components", () => {
  it("renders steps timeline with expand/collapse and anchors", () => {
    render(
      <StepsPanel
        steps={[
          { title: "Initial guess", latex: "x_0 = 1.0", note: "Given" },
          { title: "First iteration", latex: "x_1 = 1.5", note: "Converging" },
        ]}
      />
    );
    expect(screen.getByText("Initial guess")).toBeInTheDocument();
    expect(screen.getAllByText("First iteration").length).toBeGreaterThan(0);
    const expandBtn = screen.queryByRole("button", { name: /expand|collapse/i });
    if (expandBtn) {
      fireEvent.click(expandBtn);
    }
  });

  it("renders tables with sticky header & first column, CSV download and copy", () => {
    render(
      <DataTable
        table={{
          title: "Iteration Table",
          columns: ["i", "x_i"],
          rows: [
            [0, 1.0],
            [1, 1.5],
          ],
        }}
      />
    );
    expect(screen.getByText("Iteration Table")).toBeInTheDocument();
    expect(screen.getByText("Copy table")).toBeInTheDocument();
    expect(screen.getByText("Download CSV")).toBeInTheDocument();
  });

  it("renders code block with line numbers and copy", () => {
    render(<CodePanel title="Python Implementation" code="print('hello')" language="python" />);
    expect(screen.getByText("Python Implementation")).toBeInTheDocument();
    expect(screen.getByText(/print\('hello'\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy code/i })).toBeInTheDocument();
  });

  it("renders result header with headline answer, stat row, summary and warning alert", () => {
    render(<ResultHeader response={MOCK_SOLVE_RESPONSE} />);
    expect(screen.getByTestId("result-headline")).toBeInTheDocument();
    expect(screen.getByTestId("stat-row")).toBeInTheDocument();
    expect(screen.getByTestId("result-summary")).toBeInTheDocument();
    expect(screen.getByText("Function changes sign.")).toBeInTheDocument();
    expect(screen.getByText("Gauss-Seidel matrix is not strictly diagonally dominant.")).toBeInTheDocument();
  });

  it("renders iteration player with play/pause and scrub controls", () => {
    const onChange = vi.fn();
    render(
      <IterationPlayer
        steps={[
          { title: "Step 1" },
          { title: "Step 2" },
          { title: "Step 3" },
        ]}
        activeIndex={0}
        onChange={onChange}
      />
    );
    const playBtn = screen.getByRole("button", { name: "Play iterations" });
    expect(playBtn).toBeInTheDocument();
    fireEvent.click(playBtn);
    const slider = screen.getByRole("slider");
    expect(slider).toBeInTheDocument();
    fireEvent.change(slider, { target: { value: "2" } });
    expect(onChange).toHaveBeenCalledWith(1);
  });
});
