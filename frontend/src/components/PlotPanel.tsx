import { lazy, Suspense, useMemo } from "react";
import type { Config, Data, Layout } from "plotly.js";

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
  scrollZoom: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d"],
  toImageButtonOptions: { format: "png", filename: "nms-plot", scale: 2 },
};

/** Interactive Plotly graph with zoom/pan, hover values and PNG export. */
export function PlotPanel({ plot, title, height = 420 }: PlotPanelProps) {
  const mode = useThemeStore((state) => state.mode);
  const dark = resolveDark(mode);

  const layout = useMemo<Partial<Layout>>(() => {
    const axis = {
      gridcolor: dark ? "#1e293b" : "#e2e8f0",
      zerolinecolor: dark ? "#334155" : "#cbd5e1",
      color: dark ? "#cbd5e1" : "#334155",
    };
    return {
      autosize: true,
      height,
      margin: { l: 56, r: 24, t: 40, b: 48 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: dark ? "#e2e8f0" : "#0f172a", size: 12 },
      legend: { orientation: "h", y: -0.2 },
      hovermode: "closest",
      xaxis: { ...axis, zeroline: true },
      yaxis: { ...axis, zeroline: true },
      ...plot.layout,
    };
  }, [plot.layout, dark, height]);

  if (plot.traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 bg-white/50 px-6 py-12 text-center dark:border-white/10 dark:bg-white/[0.02]">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-white/[0.06] dark:text-slate-500">
          <Icon name="chart" size={19} />
        </span>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No graph is available for this result.
        </p>
      </div>
    );
  }

  return (
    <section className={`animate-fade-in overflow-hidden ${ui.card}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 px-4 py-3 dark:border-white/[0.07]">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`${ui.iconBox} h-7 w-7`}>
            <Icon name="chart" size={14} />
          </span>
          <h3 className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
            {title ?? "Graph"}
          </h3>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/80 px-2.5 py-1 text-[10px] font-medium text-slate-500 dark:border-white/10 dark:text-slate-400">
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-teal-500" />
          Interactive
        </span>
      </header>
      <div className="p-1.5 sm:p-2.5">
        <Suspense fallback={<LoadingSkeleton lines={4} className="p-4" />}>
          <Plot
            data={plot.traces as Data[]}
            layout={layout}
            config={PLOT_CONFIG}
            style={{ width: "100%", height }}
            useResizeHandler
          />
        </Suspense>
      </div>
      <footer className="flex items-center justify-between gap-2 border-t border-slate-100 px-4 py-2 text-[11px] text-slate-600 dark:border-white/[0.06] dark:text-slate-400">
        <span>Drag to pan · scroll to zoom · use the toolbar to export a PNG</span>
      </footer>
    </section>
  );
}
