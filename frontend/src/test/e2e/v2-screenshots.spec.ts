/// <reference types="node" />
import { test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const VIEWPORTS = [
  { width: 1440, height: 900, name: "1440" },
  { width: 390, height: 844, name: "390" },
];

const THEMES = ["light", "paper", "dark"];

test.describe("v2 Design System Screenshots", () => {
  for (const theme of THEMES) {
    for (const vp of VIEWPORTS) {
      test(`screenshots theme=${theme} vp=${vp.name}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });

        // 1. Home page
        await page.goto("http://localhost:5173/");
        await page.evaluate((t) => {
          localStorage.setItem("nms-theme", JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute("data-theme", t);
        }, theme);
        await page.reload();
        await page.waitForLoadState("networkidle");

        const outDir = path.join(process.cwd(), "docs/screenshots/phase-1-3");
        fs.mkdirSync(outDir, { recursive: true });

        await page.screenshot({
          path: path.join(outDir, `home-${theme}-${vp.name}.png`),
          fullPage: true,
        });

        // 2. Bisection page
        await page.goto("http://localhost:5173/methods/bisection");
        await page.evaluate((t) => {
          localStorage.setItem("nms-theme", JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute("data-theme", t);
        }, theme);
        await page.reload();
        await page.waitForLoadState("networkidle");

        await page.screenshot({
          path: path.join(outDir, `bisection-empty-${theme}-${vp.name}.png`),
          fullPage: true,
        });

        // Click solve
        const solveBtn = page.locator('button[type="submit"]', { hasText: "Solve" });
        if (await solveBtn.isVisible()) {
          await solveBtn.click();
          await page.waitForTimeout(600);
          await page.screenshot({
            path: path.join(outDir, `bisection-success-${theme}-${vp.name}.png`),
            fullPage: true,
          });
        }

        // 3. Gauss-Seidel page
        await page.goto("http://localhost:5173/methods/gauss_seidel");
        await page.evaluate((t) => {
          localStorage.setItem("nms-theme", JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute("data-theme", t);
        }, theme);
        await page.reload();
        await page.waitForLoadState("networkidle");

        await page.screenshot({
          path: path.join(outDir, `gauss-seidel-empty-${theme}-${vp.name}.png`),
          fullPage: true,
        });

        const solveGs = page.locator('button[type="submit"]', { hasText: "Solve" });
        if (await solveGs.isVisible()) {
          await solveGs.click();
          await page.waitForTimeout(600);
          await page.screenshot({
            path: path.join(outDir, `gauss-seidel-success-${theme}-${vp.name}.png`),
            fullPage: true,
          });
        }
      });
    }
  }
});
