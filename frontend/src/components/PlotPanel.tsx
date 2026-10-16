import { lazy, Suspense, useMemo } from "react";
import type { Config, Data, Layout } from "plotly.js";

import { resolveDark, useThemeStore } from "../store/theme";
import type { PlotPayload } from "../types/api";
import { ui } from "../utils/ui";
import { LoadingSkeleton } from "./LoadingSkeleton";

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
      <div className={`flex h-40 items-center justify-center ${ui.card}`}>
        <p className="text-sm text-slate-500">No graph is available for this result.</p>
      </div>
    );
  }

  return (
    <section className={ui.card}>
      {title && (
        <h3 className="border-b border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 dark:border-slate-800 dark:text-slate-200">
          {title}
        </h3>
      )}
      <div className="p-2">
        <Suspense fallback={<LoadingSkeleton lines={4} />}>
          <Plot
            data={plot.traces as Data[]}
            layout={layout}
            config={PLOT_CONFIG}
            style={{ width: "100%", height }}
            useResizeHandler
          />
        </Suspense>
      </div>
    </section>
  );
}
