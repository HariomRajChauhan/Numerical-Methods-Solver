/// <reference types="node" />
import { test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const VIEWPORTS = [
  { width: 1366, height: 768, name: "1366" },
  { width: 390, height: 844, name: "390" },
];

const THEMES = ["light", "paper", "dark"];

const METHODS = [
  { id: "newton_raphson", name: "newton-raphson" },
  { id: "simpson_13", name: "simpson-13" },
  { id: "runge_kutta_4", name: "runge-kutta-4" },
];

test.describe("v2 Phase 4 Screenshots (Newton-Raphson, Simpson 1/3, RK4)", () => {
  for (const method of METHODS) {
    for (const theme of THEMES) {
      for (const vp of VIEWPORTS) {
        test(`screenshot ${method.name} theme=${theme} vp=${vp.name}`, async ({ page }) => {
          await page.setViewportSize({ width: vp.width, height: vp.height });
          await page.goto(`/methods/${method.id}`);
          await page.evaluate((t) => {
            localStorage.setItem("nms-theme", JSON.stringify({ state: { mode: t } }));
            document.documentElement.setAttribute("data-theme", t);
          }, theme);
          await page.reload();
          await page.waitForLoadState("networkidle").catch(() => {});

          const outDir = path.join(process.cwd(), "docs/screenshots/phase-4");
          fs.mkdirSync(outDir, { recursive: true });

          // 1. Loading state / Empty state
          await page.screenshot({
            path: path.join(outDir, `${method.name}-empty-${theme}-${vp.name}.png`),
            fullPage: true,
          });

          // 2. Solve / Success state
          const solveBtn = page.locator('button[type="submit"]', { hasText: "Solve" });
          if (await solveBtn.isVisible()) {
            await solveBtn.click();
            await page.waitForTimeout(800);
            await page.screenshot({
              path: path.join(outDir, `${method.name}-success-${theme}-${vp.name}.png`),
              fullPage: true,
            });
          }
        });
      }
    }
  }

  // Failure state (x^2 + 1 on [0, 2])
  test("failure state x^2 + 1 on bisection/newton", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/methods/bisection");
    await page.evaluate((t) => {
      localStorage.setItem("nms-theme", JSON.stringify({ state: { mode: t } }));
      document.documentElement.setAttribute("data-theme", t);
    }, "dark");
    await page.reload();
    await page.waitForLoadState("networkidle").catch(() => {});

    // Fill function input with x^2 + 1
    const funcInput = page.locator('input[name="f"], input[placeholder*="function"], textarea').first();
    if (await funcInput.isVisible()) {
      await funcInput.fill("x^2 + 1");
    }
    const solveBtn = page.locator('button[type="submit"]', { hasText: "Solve" });
    if (await solveBtn.isVisible()) {
      await solveBtn.click();
      await page.waitForTimeout(800);
      const outDir = path.join(process.cwd(), "docs/screenshots/phase-4");
      fs.mkdirSync(outDir, { recursive: true });
      await page.screenshot({
        path: path.join(outDir, `bisection-failure-dark-1366.png`),
        fullPage: true,
      });
    }
  });

  // Warning state (Gauss-Seidel not diagonally dominant)
  test("warning state Gauss-Seidel not diagonally dominant", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/methods/gauss_seidel");
    await page.evaluate((t) => {
      localStorage.setItem("nms-theme", JSON.stringify({ state: { mode: t } }));
      document.documentElement.setAttribute("data-theme", t);
    }, "dark");
    await page.reload();
    await page.waitForLoadState("networkidle").catch(() => {});

    const solveBtn = page.locator('button[type="submit"]', { hasText: "Solve" });
    if (await solveBtn.isVisible()) {
      await solveBtn.click();
      await page.waitForTimeout(800);
      const outDir = path.join(process.cwd(), "docs/screenshots/phase-4");
      fs.mkdirSync(outDir, { recursive: true });
      await page.screenshot({
        path: path.join(outDir, `gauss-seidel-warning-dark-1366.png`),
        fullPage: true,
      });
    }
  });
});
