import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExportButtons } from "../components/ExportButtons";
import { downloadBlob } from "../utils/download";

vi.mock("../utils/download", () => ({
  downloadBlob: vi.fn(),
  downloadText: vi.fn(),
  copyText: vi.fn(),
  slugify: (text: string) => text,
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("ExportButtons", () => {
  it("posts to the export endpoint and downloads the blob", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("%PDF-1.4", {
        status: 200,
        headers: { "Content-Type": "application/pdf" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ExportButtons methodId="bisection" inputs={{ a: 1 }} />);
    fireEvent.click(screen.getByRole("button", { name: /Download PDF report/i }));

    await waitFor(() => expect(downloadBlob).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/export/bisection?format=pdf",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ a: 1 }) }),
    );
    expect(downloadBlob).toHaveBeenCalledTimes(1);
    const [filename, blob] = vi.mocked(downloadBlob).mock.calls[0];
    expect(filename).toBe("nms_bisection.pdf");
    expect(blob).toBeDefined();
    expect(blob.type).toBe("application/pdf");
    expect(blob.size).toBe(8);
  });

  it("shows the backend message when the export fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "not implemented yet" }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    render(<ExportButtons methodId="newton_raphson" inputs={{}} />);
    fireEvent.click(screen.getByRole("button", { name: /Download CSV report/i }));

    expect(await screen.findByText("not implemented yet")).toBeInTheDocument();
    expect(downloadBlob).not.toHaveBeenCalled();
  });
});
