import type { ReactNode } from "react";

import { ui } from "../../utils/ui";
import { Icon, type IconName } from "./Icon";

interface EmptyStateProps {
  icon?: IconName;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
  className?: string;
}

/** Consistent dashed-panel empty state for results, tables, graphs and catalogues. */
export function EmptyState({
  icon = "layers",
  title,
  description,
  action,
  compact = false,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-panel border border-dashed border-line-strong bg-surface-muted text-center ${compact ? "gap-2 px-5 py-8" : "gap-3 px-6 py-12"} ${className}`}
    >
      <span
        className={`${ui.iconBox} ${compact ? "h-9 w-9" : "h-11 w-11 rounded-panel"}`}
      >
        <Icon name={icon} size={compact ? 17 : 21} />
      </span>
      <div>
        <p className="text-sm font-semibold text-ink">{title}</p>
        {description && (
          <div className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-ink-muted">
            {description}
          </div>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
