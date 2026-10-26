import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "../components/Toaster";
import { toast, useToastStore } from "../store/toast";

describe("Toaster", () => {
  afterEach(() => {
    vi.useRealTimers();
    useToastStore.getState().clear();
  });

  it("announces a toast and dismisses it after the exit animation", () => {
    vi.useFakeTimers();
    render(<Toaster />);

    act(() => {
      toast({ tone: "success", title: "Solution ready", message: "22 steps" });
    });

    expect(screen.getByRole("status")).toHaveTextContent("Solution ready");
    expect(screen.getByRole("status")).toHaveTextContent("22 steps");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));
    expect(screen.getByRole("status")).toHaveClass("animate-toast-out");

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("auto-dismisses after its duration", () => {
    vi.useFakeTimers();
    render(<Toaster />);

    act(() => {
      toast({ tone: "error", title: "Solve failed", duration: 1000 });
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Solve failed");

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByRole("alert")).toHaveClass("animate-toast-out");

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
