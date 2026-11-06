import { useEffect } from "react";

import {
  retryBackendConnection,
  startBackendWake,
  useBackendConnectionStore,
} from "../store/connection";

/**
 * Start the automatic backend wake-up once per app session and expose the
 * shared readiness state. Mounting this more than once is harmless: the store
 * owns a single-flight health-check cycle.
 */
export function useBackendConnection() {
  const status = useBackendConnectionStore((state) => state.status);
  const error = useBackendConnectionStore((state) => state.error);

  useEffect(() => {
    startBackendWake();
  }, []);

  return {
    status,
    error,
    retry: retryBackendConnection,
  };
}
