import { useEffect } from "react";

import { useCatalogStore } from "../store/catalog";

/** Load the method catalogue once when the app mounts. */
export function useCatalog(): void {
  const load = useCatalogStore((state) => state.load);
  useEffect(() => {
    void load();
  }, [load]);
}
