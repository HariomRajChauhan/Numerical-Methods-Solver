import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StepsPanel } from "../components/StepsPanel";
import type { Step } from "../types/api";

const STEPS: Step[] = [
  { title: "Initial interval", latex: "a=1,\\ b=2", note: "f(a)f(b)<0" },
  { title: "First midpoint", latex: "c=1.5", note: "" },
];

describe("StepsPanel", () => {
  it("renders a numbered entry per step", () => {
    const { container } = render(<StepsPanel steps={STEPS} />);
    expect(screen.getAllByText("Initial interval").length).toBeGreaterThan(0);
    expect(screen.getAllByText("First midpoint").length).toBeGreaterThan(0);
    expect(container.querySelectorAll("details")).toHaveLength(STEPS.length);
  });

  it("shows the empty message when there are no steps", () => {
    render(<StepsPanel steps={[]} />);
    expect(screen.getByText(/No working steps/i)).toBeInTheDocument();
  });
});
