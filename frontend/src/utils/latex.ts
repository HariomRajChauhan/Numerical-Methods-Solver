import katex from "katex";

const ESCAPES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => ESCAPES[char] ?? char);
}

/**
 * Render a LaTeX string to KaTeX HTML.
 * Never throws: bad input falls back to escaped plain text so one malformed
 * step can never blank out the whole page.
 */
export function renderLatex(latex: string, displayMode = false): string {
  if (!latex) return "";
  try {
    return katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      strict: "ignore",
      output: "html",
      trust: false,
    });
  } catch {
    return `<span class="font-mono">${escapeHtml(latex)}</span>`;
  }
}
