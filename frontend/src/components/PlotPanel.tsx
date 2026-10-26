import { lazy, Suspense, useMemo } from "react";
import type { Config, Data, Layout } from "plotly.js";

import { buildPlotLayout, themePlotTraces } from "../design/plotTheme";
import { resolveDark, useThemeStore } from "../store/theme";
import type { PlotPayload } from "../types/api";
import { ui } from "../utils/ui";
import { LoadingSkeleton } from "./LoadingSkeleton";
import { Icon } from "./ui/Icon";

// Plotly is heavy (~1 MB gzip); keep it out of the initial bundle.
const Plot = lazy(() => import("react-plotly.js"));

interface PlotPanelProps {
  plot: PlotPayload;
  title?: string;
  height?: number;
}

const PLOT_CONFIG: Partial<Config> = {
  responsive: true,
  displaylogo: false,
  displayModeBar: "hover",
  scrollZoom: true,
  showTips: false,
  doubleClick: "reset",
  modeBarButtonsToRemove: ["lasso2d", "select2d"],
  toImageButtonOptions: { format: "png", filename: "nms-plot", scale: 2 },
};

/** Interactive Plotly graph with a shared theme, accessible palette and PNG export. */
export function PlotPanel({ plot, title, height = 420 }: PlotPanelProps) {
  const mode = useThemeStore((state) => state.mode);
  const dark = resolveDark(mode);

  const traces = useMemo(() => themePlotTraces(plot.traces, dark), [plot.traces, dark]);
  const layout = useMemo(
    () => buildPlotLayout(plot, dark, height) as Partial<Layout>,
    [plot, dark, height],
  );

  if (plot.traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-panel border border-dashed border-line-strong bg-surface-muted px-6 py-12 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-control bg-surface text-ink-subtle shadow-sm">
          <Icon name="chart" size={19} />
        </span>
        <p className="text-sm text-ink-muted">No graph is available for this result.</p>
      </div>
    );
  }

  return (
    <section className={`animate-fade-in overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name="chart" size={14} />
          </span>
          <h3 className="truncate text-sm font-semibold text-ink">{title ?? "Graph"}</h3>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-pill border border-line px-2.5 py-1 text-2xs font-medium text-ink-muted">
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-info" />
          Interactive · Okabe–Ito
        </span>
      </header>
      <div
        className="p-1.5 sm:p-2.5"
        role="group"
        aria-label={`${title ?? "Graph"}. Interactive Plotly chart. Drag to pan, scroll to zoom, or use the chart toolbar to export a PNG.`}
      >
        <Suspense fallback={<LoadingSkeleton lines={4} className="p-4" />}>
          <Plot
            data={traces as unknown as Data[]}
            layout={layout}
            config={PLOT_CONFIG}
            style={{ width: "100%", height }}
            useResizeHandler
          />
        </Suspense>
      </div>
      <footer className="flex items-center justify-between gap-2 border-t border-line px-4 py-2 text-2xs text-ink-muted">
        <span>Drag to pan · scroll to zoom · use the toolbar to export a PNG</span>
      </footer>
    </section>
  );
}
