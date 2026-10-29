import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ShortcutsSheet } from "../components/layout/ShortcutsSheet";

describe("ShortcutsSheet", () => {
  it("renders nothing while closed", () => {
    render(<ShortcutsSheet open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("exposes an accessible shortcut reference", () => {
    render(<ShortcutsSheet open onClose={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("heading", { name: /work faster with shortcuts/i })).toBeInTheDocument();
    expect(screen.getByText(/solve from an input field/i)).toBeInTheDocument();
    expect(screen.getByText(/switch between the solver tabs/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /close keyboard shortcuts/i })).toHaveFocus();
  });

  it("closes on Escape and on the close button", () => {
    const onClose = vi.fn();
    render(<ShortcutsSheet open onClose={onClose} />);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /close keyboard shortcuts/i }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
