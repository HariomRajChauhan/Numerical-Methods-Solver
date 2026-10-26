import { describe, expect, it } from "vitest";

import { OKABE_ITO_COLORWAY, buildPlotLayout, themePlotTraces } from "../design/plotTheme";
import type { PlotPayload, PlotTrace } from "../types/api";

describe("plot theme", () => {
  it("maps backend traces onto the Okabe-Ito palette", () => {
    const traces: PlotTrace[] = [
      { type: "scatter", mode: "lines", name: "f(x) = x", x: [], y: [] },
      {
        type: "scatter",
        mode: "lines",
        name: "tangent 1",
        x: [],
        y: [],
        line: { color: "#f59e0b", dash: "dash", width: 1 },
      },
      {
        type: "scatter",
        mode: "markers",
        name: "root",
        x: [1],
        y: [0],
        marker: { color: "#dc2626", size: 11 },
      },
    ];

    const themed = themePlotTraces(traces, false);
    expect((themed[0].line as Record<string, unknown>).color).toBe("#0072B2");
    expect((themed[1].line as Record<string, unknown>).color).toBe("#E69F00");
    expect((themed[1].line as Record<string, unknown>).dash).toBe("dash");
    expect((themed[1].line as Record<string, unknown>).width).toBe(1);
    expect((themed[2].marker as Record<string, unknown>).color).toBe("#D55E00");
  });

  it("themes heatmaps with a diverging Okabe-Ito scale", () => {
    const [trace] = themePlotTraces(
      [{ type: "heatmap", z: [[1]], colorscale: "RdBu_r" }],
      true,
    );
    expect(trace.colorscale).toEqual([
      [0, "#56B4E9"],
      [0.5, "#111a2c"],
      [1, "#E69F00"],
    ]);
  });

  it("merges solver labels with themed axes and a shared colorway", () => {
    const plot: PlotPayload = {
      traces: [],
      layout: {
        title: { text: "Bisection on [1, 2]" },
        xaxis: { title: { text: "x" }, zeroline: true },
      },
    };

    const layout = buildPlotLayout(plot, false, 420);
    const title = layout.title as Record<string, unknown>;
    const xaxis = layout.xaxis as Record<string, unknown>;
    const axisTitle = xaxis.title as Record<string, unknown>;

    expect(title.text).toBe("Bisection on [1, 2]");
    expect(xaxis.gridcolor).toBe("#e2e8f0");
    expect(axisTitle.text).toBe("x");
    expect(layout.colorway).toEqual(OKABE_ITO_COLORWAY);
    expect(layout.height).toBe(420);
  });
});
