import { useEffect, useState } from "react";

interface LatexViewProps {
  latex: string;
  /** Display (block, centred) vs inline rendering. */
  display?: boolean;
  className?: string;
}

type Renderer = typeof import("../utils/latex");

let rendererPromise: Promise<Renderer> | null = null;

function loadRenderer(): Promise<Renderer> {
  rendererPromise ??= import("../utils/latex");
  return rendererPromise;
}

function escapeHtml(text: string): string {
  return text.replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char] ?? char,
  );
}

/**
 * Renders a LaTeX string with KaTeX.
 * KaTeX and its stylesheet load on demand so the rest of the solver route can
 * paint before the math renderer is needed. Bad input falls back to escaped
 * plain text, and \trust is disabled so user input can never inject markup.
 */
export function LatexView({ latex, display = false, className }: LatexViewProps) {
  const [rendered, setRendered] = useState<{
    latex: string;
    display: boolean;
    html: string;
  } | null>(null);

  useEffect(() => {
    if (!latex) return;
    let active = true;
    void loadRenderer()
      .then(({ renderLatex }) => {
        if (active) setRendered({ latex, display, html: renderLatex(latex, display) });
      })
      .catch(() => {
        if (active) setRendered({ latex, display, html: escapeHtml(latex) });
      });
    return () => {
      active = false;
    };
  }, [latex, display]);

  if (!latex) return null;
  const html =
    rendered?.latex === latex && rendered.display === display ? rendered.html : escapeHtml(latex);
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
