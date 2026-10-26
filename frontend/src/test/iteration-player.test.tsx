import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { IterationPlayer } from "../components/IterationPlayer";

const STEPS = [{ title: "Setup" }, { title: "Iteration 1" }, { title: "Iteration 2" }];

function Harness({ initial = 0 }: { initial?: number }) {
  const [active, setActive] = useState(initial);
  return <IterationPlayer steps={STEPS} activeIndex={active} onChange={setActive} />;
}

describe("IterationPlayer", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("moves through steps with the previous and next controls", () => {
    render(<Harness />);
    const slider = screen.getByRole("slider", { name: "Iteration step" });

    expect(slider).toHaveValue("1");
    fireEvent.click(screen.getByRole("button", { name: "Next step" }));
    expect(slider).toHaveValue("2");
    expect(screen.getByRole("button", { name: "Previous step" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Previous step" }));
    expect(slider).toHaveValue("1");
  });

  it("plays through the steps and stops at the final one", () => {
    vi.useFakeTimers();
    render(<Harness />);
    const slider = screen.getByRole("slider", { name: "Iteration step" });

    fireEvent.click(screen.getByRole("button", { name: "Play iterations" }));
    expect(screen.getByRole("button", { name: "Pause playback" })).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(slider).toHaveValue("2");

    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(slider).toHaveValue("3");
    expect(screen.getByRole("button", { name: "Play iterations" })).toBeInTheDocument();
  });

  it("restarts from the first step when play is pressed at the end", () => {
    render(<Harness initial={2} />);
    expect(screen.getByRole("slider", { name: "Iteration step" })).toHaveValue("3");

    fireEvent.click(screen.getByRole("button", { name: "Play iterations" }));
    expect(screen.getByRole("slider", { name: "Iteration step" })).toHaveValue("1");
    expect(screen.getByRole("button", { name: "Pause playback" })).toBeInTheDocument();
  });
});
