import type { PlotPayload, PlotTrace } from "../types/api";

/**
 * Okabe–Ito colour-blind-safe palette.
 * https://jfly.uni-koeln.de/color/
 *
 * The black swatch is replaced by the theme ink so it remains visible on dark
 * plots; all other hues are the canonical Okabe–Ito values.
 */
const OKABE_ITO = {
  blue: "#0072B2",
  orange: "#E69F00",
  green: "#009E73",
  yellow: "#F0E442",
  sky: "#56B4E9",
  vermillion: "#D55E00",
  purple: "#CC79A7",
  grey: "#64748B",
  ink: "#111827",
} as const;

export const OKABE_ITO_COLORWAY = [
  OKABE_ITO.blue,
  OKABE_ITO.orange,
  OKABE_ITO.green,
  OKABE_ITO.purple,
  OKABE_ITO.sky,
  OKABE_ITO.vermillion,
  OKABE_ITO.grey,
  OKABE_ITO.yellow,
] as const;

export const DARK_OKABE_ITO_COLORWAY = [
  OKABE_ITO.sky,
  OKABE_ITO.orange,
  OKABE_ITO.green,
  OKABE_ITO.purple,
  OKABE_ITO.blue,
  OKABE_ITO.vermillion,
  "#94A3B8",
  OKABE_ITO.yellow,
] as const;

interface PlotTheme {
  font: string;
  axis: string;
  grid: string;
  zero: string;
  hover: string;
  modebar: string;
  accent: string;
  dark: boolean;
}

const FALLBACK_THEME: Record<"light" | "dark", PlotTheme> = {
  light: {
    font: "#0f172a",
    axis: "#475569",
    grid: "#e2e8f0",
    zero: "#cbd5e1",
    hover: "#ffffff",
    modebar: "#475569",
    accent: "#4338ca",
    dark: false,
  },
  dark: {
    font: "#f1f5f9",
    axis: "#cbd5e1",
    grid: "#1e293b",
    zero: "#334155",
    hover: "#111a2c",
    modebar: "#cbd5e1",
    accent: "#a5b4fc",
    dark: true,
  },
};

/** Read the plot tokens from the active theme, with stable SSR/test fallbacks. */
export function resolvePlotTheme(dark: boolean): PlotTheme {
  const fallback = FALLBACK_THEME[dark ? "dark" : "light"];
  if (typeof window === "undefined" || typeof document === "undefined") return fallback;
  const styles = window.getComputedStyle(document.documentElement);
  const read = (name: string, fallbackValue: string): string =>
    styles.getPropertyValue(name).trim() || fallbackValue;
  return {
    font: read("--plot-font", fallback.font),
    axis: read("--plot-axis", fallback.axis),
    grid: read("--plot-grid", fallback.grid),
    zero: read("--plot-zero", fallback.zero),
    hover: read("--plot-hover", fallback.hover),
    modebar: read("--plot-modebar", fallback.modebar),
    accent: read("--color-accent-text", fallback.accent),
    dark,
  };
}

const LEGACY_COLOR_MAP: Record<string, keyof typeof OKABE_ITO> = {
  "#dc2626": "vermillion",
  "#ef4444": "vermillion",
  "#f43f5e": "vermillion",
  "#2563eb": "blue",
  "#3b82f6": "blue",
  "#6366f1": "blue",
  "#4f46e5": "blue",
  "#7c3aed": "purple",
  "#8b5cf6": "purple",
  "#16a34a": "green",
  "#059669": "green",
  "#10b981": "green",
  "#f59e0b": "orange",
  "#eab308": "orange",
  "#94a3b8": "grey",
  "#64748b": "grey",
  "#111827": "ink",
  "#0f172a": "ink",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function paletteFor(dark: boolean): Record<keyof typeof OKABE_ITO, string> {
  return dark ? { ...OKABE_ITO, ink: "#e2e8f0" } : OKABE_ITO;
}

function colorwayFor(dark: boolean): readonly string[] {
  return dark ? DARK_OKABE_ITO_COLORWAY : OKABE_ITO_COLORWAY;
}

/** Map a legacy backend colour to the closest Okabe–Ito hue. */
function mapLegacyColor(value: unknown, dark: boolean): string | null {
  if (typeof value !== "string") return null;
  const key = value.trim().toLowerCase();
  const swatch = LEGACY_COLOR_MAP[key];
  return swatch ? paletteFor(dark)[swatch] : null;
}

function roleColor(name: string, index: number, dark: boolean): string {
  const palette = paletteFor(dark);
  const colourway = colorwayFor(dark);
  const lower = name.toLowerCase();
  if (/^(tangent|secant)\s+\d+/.test(lower)) return palette.orange;
  if (lower.includes("root") || lower.includes("fixed point") || lower.includes("prediction")) {
    return palette.vermillion;
  }
  if (lower.includes("exact")) return palette.green;
  if (lower.includes("iterat")) return palette.blue;
  if (lower.includes("residual") || lower.includes("error")) return palette.orange;
  if (lower.includes("data point")) return palette.sky;
  if (/\bf\(x\)|\bg\(x\)|fitted curve|function|solution/.test(lower)) return palette.blue;
  return colourway[index % colourway.length];
}

function traceColor(
  trace: Record<string, unknown>,
  index: number,
  dark: boolean,
): string {
  const explicit = isRecord(trace.line) ? trace.line.color : undefined;
  const marker = isRecord(trace.marker) ? trace.marker.color : undefined;
  const candidate = typeof explicit === "string" ? explicit : typeof marker === "string" ? marker : undefined;
  const legacy = mapLegacyColor(candidate, dark);
  if (legacy) return legacy;
  return roleColor(String(trace.name ?? ""), index, dark);
}

function mapMarkerColor(
  value: unknown,
  trace: Record<string, unknown>,
  index: number,
  dark: boolean,
): unknown {
  if (Array.isArray(value)) {
    const fallback = traceColor(trace, index, dark);
    return value.map((entry) => mapLegacyColor(entry, dark) ?? fallback);
  }
  return mapLegacyColor(value, dark) ?? traceColor(trace, index, dark);
}

function heatmapScale(dark: boolean): [number, string][] {
  return dark
    ? [
        [0, "#56B4E9"],
        [0.5, "#111a2c"],
        [1, "#E69F00"],
      ]
    : [
        [0, "#0072B2"],
        [0.5, "#f7f8fc"],
        [1, "#D55E00"],
      ];
}

/** Apply the shared palette and interaction colours to every trace. */
export function themePlotTraces(traces: PlotTrace[], dark: boolean): PlotTrace[] {
  const theme = resolvePlotTheme(dark);
  return traces.map((trace, index) => {
    const source = trace as Record<string, unknown>;
    const next: Record<string, unknown> = { ...source };
    const type = String(source.type ?? "scatter");
    const mode = String(source.mode ?? "");
    const color = traceColor(source, index, dark);

    if (type === "heatmap" || type === "contour" || type === "heatmapgl") {
      next.colorscale = heatmapScale(dark);
      const colorbar = isRecord(source.colorbar) ? { ...source.colorbar } : {};
      next.colorbar = {
        ...colorbar,
        outlinecolor: theme.grid,
        outlinewidth: 1,
        tickfont: { color: theme.axis, size: 11 },
        title: {
          ...(isRecord(colorbar.title) ? colorbar.title : {}),
          font: { color: theme.axis, size: 11 },
        },
      };
      return next;
    }

    if (type === "bar" || type === "histogram") {
      const marker = isRecord(source.marker) ? { ...source.marker } : {};
      next.marker = {
        ...marker,
        color: mapMarkerColor(marker.color, source, index, dark),
        line: isRecord(marker.line)
          ? { ...marker.line, color: mapLegacyColor(marker.line.color, dark) ?? color }
          : marker.line,
      };
      return next;
    }

    if (!(mode.includes("lines") || mode.includes("markers"))) return next;

    if (mode.includes("lines")) {
      const line = isRecord(source.line) ? { ...source.line } : {};
      next.line = {
        ...line,
        color: mapLegacyColor(line.color, dark) ?? color,
        width: typeof line.width === "number" ? line.width : 2.2,
      };
    }
    if (mode.includes("markers")) {
      const marker = isRecord(source.marker) ? { ...source.marker } : {};
      next.marker = {
        ...marker,
        color: mapMarkerColor(marker.color, source, index, dark),
        size: typeof marker.size === "number" ? marker.size : 7,
      };
    }
    return next;
  });
}

function axisTheme(theme: PlotTheme): Record<string, unknown> {
  return {
    color: theme.axis,
    gridcolor: theme.grid,
    gridwidth: 1,
    zerolinecolor: theme.zero,
    zerolinewidth: 1,
    linecolor: theme.grid,
    tickcolor: theme.grid,
    tickfont: { color: theme.axis, size: 11 },
    title: { font: { color: theme.axis, size: 12 } },
  };
}

function mergeTitle(
  base: Record<string, unknown>,
  source: Record<string, unknown>,
): Record<string, unknown> {
  const sourceTitle = isRecord(source)
    ? source
    : typeof source === "string"
      ? { text: source }
      : {};
  return { ...sourceTitle, ...base, font: { ...(base.font as object), ...(isRecord(sourceTitle.font) ? sourceTitle.font : {}) } };
}

/**
 * Build a Plotly layout that follows the app theme, while preserving every
 * axis, annotation and title supplied by the solver.
 */
export function buildPlotLayout(
  plot: PlotPayload,
  dark: boolean,
  height: number,
): Record<string, unknown> {
  const theme = resolvePlotTheme(dark);
  const source = isRecord(plot.layout) ? (plot.layout as Record<string, unknown>) : {};
  const axis = axisTheme(theme);
  const base: Record<string, unknown> = {
    autosize: true,
    height,
    dragmode: "pan",
    margin: { l: 56, r: 24, t: 48, b: 48 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    colorway: colorwayFor(dark),
    font: {
      family: "'Inter', ui-sans-serif, system-ui, sans-serif",
      size: 12,
      color: theme.font,
    },
    title: {
      x: 0,
      xanchor: "left",
      font: { color: theme.font, size: 15 },
    },
    legend: {
      orientation: "h",
      y: -0.2,
      x: 0,
      font: { color: theme.axis, size: 11 },
      bgcolor: "rgba(0,0,0,0)",
      bordercolor: theme.grid,
      borderwidth: 0,
    },
    hovermode: "closest",
    hoverlabel: {
      bgcolor: theme.hover,
      bordercolor: theme.grid,
      font: {
        family: "'Inter', ui-sans-serif, system-ui, sans-serif",
        color: theme.font,
        size: 12,
      },
    },
    modebar: {
      bgcolor: "rgba(0,0,0,0)",
      color: theme.modebar,
      activecolor: theme.accent,
    },
    xaxis: { ...axis },
    yaxis: { ...axis },
  };

  const merged: Record<string, unknown> = { ...base, ...source };
  const axisKeys = new Set([
    ...Object.keys(base).filter((key) => /^[xy]axis\d*$/.test(key)),
    ...Object.keys(source).filter((key) => /^[xy]axis\d*$/.test(key)),
  ]);
  for (const key of axisKeys) {
    const baseAxis = key.startsWith("y") ? base.yaxis : base.xaxis;
    const sourceAxis = isRecord(source[key]) ? source[key] : {};
    merged[key] = {
      ...sourceAxis,
      ...(baseAxis as Record<string, unknown>),
      title: mergeTitle(
        (baseAxis as Record<string, unknown>).title as Record<string, unknown>,
        sourceAxis.title as Record<string, unknown>,
      ),
      tickfont: {
        ...((baseAxis as Record<string, unknown>).tickfont as object),
        ...(isRecord(sourceAxis.tickfont) ? sourceAxis.tickfont : {}),
      },
    };
  }

  merged.title = mergeTitle(
    base.title as Record<string, unknown>,
    (source.title ?? {}) as Record<string, unknown>,
  );
  merged.font = { ...(base.font as object), ...(isRecord(source.font) ? source.font : {}) };
  merged.legend = {
    ...(base.legend as object),
    ...(isRecord(source.legend) ? source.legend : {}),
  };
  merged.hoverlabel = {
    ...(base.hoverlabel as object),
    ...(isRecord(source.hoverlabel) ? source.hoverlabel : {}),
  };
  merged.modebar = {
    ...(base.modebar as object),
    ...(isRecord(source.modebar) ? source.modebar : {}),
  };
  merged.margin = {
    ...(base.margin as object),
    ...(isRecord(source.margin) ? source.margin : {}),
  };
  merged.colorway = colorwayFor(dark);

  if (isRecord(source.scene)) {
    const scene = source.scene;
    const sceneAxis = { ...axis, backgroundcolor: "rgba(0,0,0,0)" };
    merged.scene = {
      ...scene,
      xaxis: { ...sceneAxis, ...(isRecord(scene.xaxis) ? scene.xaxis : {}) },
      yaxis: { ...sceneAxis, ...(isRecord(scene.yaxis) ? scene.yaxis : {}) },
      zaxis: { ...sceneAxis, ...(isRecord(scene.zaxis) ? scene.zaxis : {}) },
    };
  }

  return merged;
}
