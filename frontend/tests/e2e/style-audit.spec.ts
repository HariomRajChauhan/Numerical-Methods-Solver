import { test, expect } from '@playwright/test';

const THEMES = ['light', 'paper', 'dark'];
const URLS = ['/methods/bisection', '/methods/gauss_seidel'];

test.describe('Design System v2 Style Audit', () => {
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

        // 2. Cards/panels non-zero radius
        const panels = page.locator('.rounded-lg, .rounded-panel, .rounded-control, .rounded-md, .rounded-2xl');
        const count = await panels.count();
        for (let i = 0; i < Math.min(count, 5); i++) {
          const el = panels.nth(i);
          const borderRadius = await el.evaluate((node) => window.getComputedStyle(node).borderRadius);
          expect(borderRadius).not.toBe('0px');
        }
      });
    }
  }
});
