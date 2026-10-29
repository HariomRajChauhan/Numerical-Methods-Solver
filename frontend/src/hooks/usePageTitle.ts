import { useEffect } from "react";

export const SITE_NAME = "Numerical Methods Solver";

/** Keep the document title in sync with the current page. */
export function usePageTitle(title?: string): void {
  useEffect(() => {
    document.title = title ? `${title} · ${SITE_NAME}` : SITE_NAME;
  }, [title]);
}
