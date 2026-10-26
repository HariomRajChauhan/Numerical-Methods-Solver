import { useState } from "react";

import { copyText } from "../utils/download";
import { ui } from "../utils/ui";
import { Icon } from "./ui/Icon";

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

/** Copies text to the clipboard and confirms visually for a moment. */
export function CopyButton({ text, label = "Copy", className = "" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy(): Promise<void> {
    const ok = await copyText(text);
    if (!ok) return;
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      className={`${ui.btnGhost} ${className}`}
      aria-live="polite"
    >
      <Icon name={copied ? "check" : "copy"} size={13} />
      {copied ? "Copied" : label}
    </button>
  );
}
