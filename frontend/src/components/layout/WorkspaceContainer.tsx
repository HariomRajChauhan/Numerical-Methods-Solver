import { useCallback, useEffect } from "react";
import { useLocation } from "react-router-dom";

import { useSidebarStore } from "../../store/sidebar";

/**
 * Wraps the main workspace. In focus mode the sidebar and header are hidden
 * and the workspace takes the full viewport. Press F or Escape to exit.
 */
export function WorkspaceContainer({ children }: { children: React.ReactNode }) {
  const { focusMode, setFocusMode } = useSidebarStore(
    (state) => ({ focusMode: state.focusMode, setFocusMode: state.setFocusMode })
  );
  const location = useLocation();

  // Reset focus mode when navigating to a new page.
  useEffect(() => {
    if (focusMode) setFocusMode(false);
  }, [location.pathname, focusMode, setFocusMode]);

  const toggleFocus = useCallback(() => {
    setFocusMode(!focusMode);
  }, [focusMode, setFocusMode]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Only respond when not typing in a field.
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable === true;
      if (typing) return;

      if (event.key === "f" || event.key === "F") {
        event.preventDefault();
        toggleFocus();
      } else if (event.key === "Escape" && focusMode) {
        event.preventDefault();
        setFocusMode(false);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [focusMode, toggleFocus, setFocusMode]);

  const bodyStyle: React.CSSProperties = {};
  if (focusMode) {
    bodyStyle.overflow = "hidden";
  }

  return (
    <div
      id="workspace-container"
      data-focus={focusMode}
      style={bodyStyle}
      className="relative min-h-dvh"
    >
      {children}
    </div>
  );
}
