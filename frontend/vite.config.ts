import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // Local dev: forward API calls to the FastAPI backend so requests are
      // same-origin (no CORS preflight, works from localhost/127.0.0.1/LAN).
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    proxy: {
      // Keep `vite preview` usable for Lighthouse and manual checks.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 800,
    rolldownOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          // Plotly, mathjs and KaTeX are imported on demand, so each gets its
          // own chunk and stays out of the initial route payload.
          if (id.includes("plotly")) return "vendor-plotly";
          if (id.includes("mathjs")) return "vendor-mathjs";
          if (id.includes("katex")) return "vendor-katex";
          return "vendor";
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
