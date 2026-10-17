/**
 * Folds unicode / word-processor notation into the ASCII form the parser
 * expects. Mirrors the backend parser; used for the client-side KaTeX preview
 * (the backend remains the single source of truth for what is accepted).
 *
 *   "−" -> "-"      "×" -> "*"     "÷" -> "/"
 *   "π" -> "pi"     "√(" -> "sqrt("
 *   "²" -> "^2"     "x²³" -> "x^23"
 */
const SUPERSCRIPTS: Record<string, string> = {
  "\u2070": "0",
  "\u00b9": "1",
  "\u00b2": "2",
  "\u00b3": "3",
  "\u2074": "4",
  "\u2075": "5",
  "\u2076": "6",
  "\u2077": "7",
  "\u2078": "8",
  "\u2079": "9",
};

const SUPERSCRIPT_RE = /[\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079]+/g;

export function normalizeMath(input: string): string {
  const folded = input
    .replace(/\u221a\(/g, "sqrt(")
    .replace(/[\u2212\u2013\u2014]/g, "-")
    .replace(/[\u00d7\u22c5\u00b7\u2219]/g, "*")
    .replace(/[\u00f7\u2044]/g, "/")
    .replace(/\u03c0/g, "pi")
    .replace(/\u00a0/g, " ");

  return folded.replace(
    SUPERSCRIPT_RE,
    (run) => `^${[...run].map((char) => SUPERSCRIPTS[char]).join("")}`,
  );
}
