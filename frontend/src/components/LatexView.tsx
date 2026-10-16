import { useMemo } from "react";

import { renderLatex } from "../utils/latex";

interface LatexViewProps {
  latex: string;
  /** Display (block, centred) vs inline rendering. */
  display?: boolean;
  className?: string;
}

/**
 * Renders a LaTeX string with KaTeX.
 * KaTeX output is safe HTML; user input can never inject markup because we
 * disable \trust and fall back to escaped text on failure.
 */
export function LatexView({ latex, display = false, className }: LatexViewProps) {
  const html = useMemo(() => renderLatex(latex, display), [latex, display]);
  if (!latex) return null;
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
