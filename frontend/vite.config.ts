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
  build: {
    chunkSizeWarningLimit: 800,
    rolldownOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          // Plotly stays in its own dynamically-imported chunk (never in the
          // initial bundle); mathjs/katex load up-front but cache separately.
          if (id.includes("plotly")) return undefined;
          if (id.includes("mathjs") || id.includes("katex")) return "vendor-math";
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
