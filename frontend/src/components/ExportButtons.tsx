import { useState } from "react";

import { api, ApiError, type ExportFormat } from "../api/client";
import { toast } from "../store/toast";
import { downloadBlob } from "../utils/download";
import { ui } from "../utils/ui";
import { Icon } from "./ui/Icon";

interface ExportButtonsProps {
  methodId: string;
  inputs: Record<string, unknown>;
  /** Hide the repeated "Export" label when embedded in a toolbar. */
  compact?: boolean;
}

const FORMATS: ExportFormat[] = ["pdf", "csv"];

/** Download the solved problem as a server-rendered PDF or CSV report. */
export function ExportButtons({ methodId, inputs, compact = false }: ExportButtonsProps) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport(format: ExportFormat): Promise<void> {
    setBusy(format);
    setError(null);
    try {
      const blob = await api.exportReport(methodId, inputs, format);
      downloadBlob(`nms_${methodId}.${format}`, blob);
      toast({
        tone: "success",
        title: `${format.toUpperCase()} report downloaded`,
        message: "The export includes the inputs, answer and working.",
        duration: 3200,
      });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Export failed. Please try again.";
      setError(message);
      toast({ tone: "error", title: "Export failed", message });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {!compact && (
        <span className="hidden items-center gap-1 text-2xs font-medium text-ink-muted sm:inline-flex">
          <Icon name="download" size={13} />
          Export
        </span>
      )}
      {FORMATS.map((format) => (
        <button
          key={format}
          type="button"
          disabled={busy !== null}
          onClick={() => void handleExport(format)}
          aria-label={`Download ${format.toUpperCase()} report`}
          className={`${ui.btn} px-2.5 py-1.5 text-xs`}
        >
          <Icon
            name={busy === format ? "loader" : "file"}
            size={13}
            className={busy === format ? "animate-spin" : undefined}
          />
          {format.toUpperCase()}
        </button>
      ))}
      {error && <span className="text-2xs font-medium text-danger">{error}</span>}
    </div>
  );
}
