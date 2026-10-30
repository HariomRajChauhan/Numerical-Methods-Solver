const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  const viewports = [
    { width: 1440, height: 900, name: '1440' },
    { width: 390, height: 844, name: '390' },
  ];
  const themes = ['light', 'paper', 'dark'];
  const outDir = path.join(process.cwd(), 'docs/screenshots/phase-1-3');
  fs.mkdirSync(outDir, { recursive: true });

  // Start preview server or assume dev server is running on 5173
  for (const theme of themes) {
    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // Home
      try {
        await page.goto('http://localhost:5173/', { timeout: 5000 });
        await page.evaluate((t) => {
          localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute('data-theme', t);
        }, theme);
        await page.reload();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await page.screenshot({ path: path.join(outDir, `home-${theme}-${vp.name}.png`), fullPage: true });
      } catch (e) {
        console.error('Home error:', e.message);
      }

      // Bisection
      try {
        await page.goto('http://localhost:5173/methods/bisection', { timeout: 5000 });
        await page.evaluate((t) => {
          localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute('data-theme', t);
        }, theme);
        await page.reload();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await page.screenshot({ path: path.join(outDir, `bisection-empty-${theme}-${vp.name}.png`), fullPage: true });

        const solveBtn = page.locator('button[type="submit"]', { hasText: 'Solve' });
        if (await solveBtn.isVisible()) {
          await solveBtn.click();
          await page.waitForTimeout(800);
          await page.screenshot({ path: path.join(outDir, `bisection-success-${theme}-${vp.name}.png`), fullPage: true });
        }
      } catch (e) {
        console.error('Bisection error:', e.message);
      }

      // Gauss-Seidel
      try {
        await page.goto('http://localhost:5173/methods/gauss_seidel', { timeout: 5000 });
        await page.evaluate((t) => {
          localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute('data-theme', t);
        }, theme);
        await page.reload();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await page.screenshot({ path: path.join(outDir, `gauss-seidel-empty-${theme}-${vp.name}.png`), fullPage: true });

        const solveGs = page.locator('button[type="submit"]', { hasText: 'Solve' });
        if (await solveGs.isVisible()) {
          await solveGs.click();
          await page.waitForTimeout(800);
          await page.screenshot({ path: path.join(outDir, `gauss-seidel-success-${theme}-${vp.name}.png`), fullPage: true });
        }
      } catch (e) {
        console.error('Gauss-Seidel error:', e.message);
      }
    }
  }

  await browser.close();
  console.log('Screenshots completed.');
})();
