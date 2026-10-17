import { useLayoutEffect, useRef, useState, type RefObject } from "react";

export type KeypadAction =
  | { type: "insert"; text: string; caretOffset?: number }
  | { type: "backspace" }
  | { type: "clear" }
  | { type: "left" }
  | { type: "right" };

/** Default localStorage key: shared show/hide preference for expression keypads. */
export const KEYPAD_STORAGE_KEY = "nms.keypad.open";
/** Separate preference for the compact numeric keypads (matrix / vector). */
export const NUMERIC_KEYPAD_STORAGE_KEY = "nms.keypad.numeric.open";

function readStoredOpen(storageKey: string): boolean {
  try {
    return window.localStorage.getItem(storageKey) === "1";
  } catch {
    return false;
  }
}

function writeStoredOpen(storageKey: string, open: boolean): void {
  try {
    window.localStorage.setItem(storageKey, open ? "1" : "0");
  } catch {
    // Ignore (private mode / storage disabled): the keypad still works, it just
    // will not remember the preference.
  }
}

/**
 * On-screen keypad support for a text-like input.
 *
 * The caller owns the input ref; this hook exposes the shared show/hide state
 * (persisted in localStorage) and an action handler that edits the current value
 * at the caret (or over the selection) and restores the caret afterwards.
 */
export function useKeypadInput<T extends HTMLInputElement | HTMLTextAreaElement>(
  ref: RefObject<T | null>,
  value: string,
  onChange: (next: string) => void,
  storageKey: string = KEYPAD_STORAGE_KEY,
) {
  const [show, setShow] = useState(() => readStoredOpen(storageKey));
  const pendingCaret = useRef<[number, number] | null>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (element && pendingCaret.current) {
      const [start, end] = pendingCaret.current;
      pendingCaret.current = null;
      element.focus();
      element.setSelectionRange(start, end);
    }
  });

  function toggle(): void {
    setShow((current) => {
      const next = !current;
      writeStoredOpen(storageKey, next);
      return next;
    });
  }

  function handleAction(action: KeypadAction): void {
    const element = ref.current;
    const start = element?.selectionStart ?? value.length;
    const end = element?.selectionEnd ?? value.length;

    switch (action.type) {
      case "clear":
        pendingCaret.current = [0, 0];
        onChange("");
        return;

      case "backspace":
        if (start === end && start > 0) {
          pendingCaret.current = [start - 1, start - 1];
          onChange(value.slice(0, start - 1) + value.slice(start));
        } else if (start !== end) {
          pendingCaret.current = [start, start];
          onChange(value.slice(0, start) + value.slice(end));
        }
        return;

      case "left":
      case "right": {
        if (!element) return;
        element.focus();
        let target: number;
        if (start !== end) {
          target = action.type === "left" ? start : end;
        } else {
          target =
            action.type === "left" ? Math.max(0, start - 1) : Math.min(value.length, start + 1);
        }
        element.setSelectionRange(target, target);
        return;
      }

      default: {
        const text = action.text;
        const caret = start + text.length - (action.caretOffset ?? 0);
        pendingCaret.current = [caret, caret];
        onChange(value.slice(0, start) + text + value.slice(end));
      }
    }
  }

  return {
    show,
    toggle,
    handleAction,
  };
}
