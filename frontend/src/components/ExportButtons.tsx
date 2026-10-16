import { useState } from "react";

import { api, ApiError, type ExportFormat } from "../api/client";
import { downloadBlob } from "../utils/download";
import { ui } from "../utils/ui";

interface ExportButtonsProps {
  methodId: string;
  inputs: Record<string, unknown>;
}

const FORMATS: ExportFormat[] = ["pdf", "csv"];

/** Download the solved problem as a server-rendered PDF or CSV report. */
export function ExportButtons({ methodId, inputs }: ExportButtonsProps) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport(format: ExportFormat): Promise<void> {
    setBusy(format);
    setError(null);
    try {
      const blob = await api.exportReport(methodId, inputs, format);
      downloadBlob(`nms_${methodId}.${format}`, blob);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Export report:</span>
      {FORMATS.map((format) => (
        <button
          key={format}
          type="button"
          disabled={busy !== null}
          onClick={() => void handleExport(format)}
          aria-label={`Download ${format.toUpperCase()} report`}
          className={`${ui.btnGhost} border border-slate-200 disabled:opacity-40 dark:border-slate-800`}
        >
          ⤓ {format.toUpperCase()}
        </button>
      ))}
      {error && <span className="text-xs text-rose-600 dark:text-rose-400">{error}</span>}
    </div>
  );
}
