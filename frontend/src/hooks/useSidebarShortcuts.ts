import { useEffect } from "react";

/**
 * Registers global sidebar shortcuts:
 *  - Ctrl+B / ⌘B : cycle sidebar state (expanded → rail → hidden → expanded)
 *  - F           : toggle focus mode (hides header + sidebar)
 *  - Escape      : exit focus mode
 *
 * Shortcuts are ignored when the user is typing in a text field.
 */
export function useSidebarShortcuts({
  onCycle,
  onFocusToggle,
}: {
  onCycle: () => void;
  onFocusToggle: () => void;
}): void {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if (typing) return;

      // Ctrl+B / ⌘B: cycle sidebar state
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        onCycle();
        return;
      }

      // F: toggle focus mode (ignored when typing)
      if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        onFocusToggle();
        return;
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onCycle, onFocusToggle]);
}
