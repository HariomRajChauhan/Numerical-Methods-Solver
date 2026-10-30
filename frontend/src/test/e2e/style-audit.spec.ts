/// <reference types="node" />
import { test, expect } from '@playwright/test';

const THEMES = ['light', 'paper', 'dark'];
const URLS = [
  '/methods/bisection',
  '/methods/gauss_seidel',
  '/methods/newton_raphson',
  '/methods/simpson_13',
  '/methods/runge_kutta_4',
];

test.describe('Design System v2 Style Audit (Phase 4)', () => {
  for (const url of URLS) {
    for (const theme of THEMES) {
      test(`audit url=${url} theme=${theme}`, async ({ page }) => {
        await page.setViewportSize({ width: 1366, height: 768 });
        await page.goto(`http://localhost:5173${url}`);
        await page.evaluate((t) => {
          localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute('data-theme', t);
        }, theme);
        await page.reload();
        await page.waitForLoadState('networkidle').catch(() => {});

        // 1. Hamburger center X = 28 +/- 0.5
        const hamburger = page.locator('header button[aria-label="Toggle sidebar"]');
        if (await hamburger.isVisible()) {
          const box = await hamburger.boundingBox();
          if (box) {
            const centerX = box.x + box.width / 2;
            console.log(`[MEASUREMENT] Hamburger center X: ${centerX} (target 28)`);
            expect(Math.abs(centerX - 28)).toBeLessThanOrEqual(0.5);
          }
        }

        // 2. Cards, panels, tables, steps have non-zero radius and token borders
        const elements = page.locator('.rounded-lg, .rounded-panel, .rounded-control, .rounded-md, .rounded-2xl, table, details');
        const count = await elements.count();
        for (let i = 0; i < Math.min(count, 8); i++) {
          const el = elements.nth(i);
          const borderRadius = await el.evaluate((node) => window.getComputedStyle(node).borderRadius);
          expect(borderRadius).not.toBe('0px');
        }
      });
    }
  }
});
