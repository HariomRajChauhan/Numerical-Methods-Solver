const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  const viewports = [
    { width: 1366, height: 768, name: '1366' },
    { width: 390, height: 844, name: '390' },
  ];
  const themes = ['light', 'paper', 'dark'];
  const outDir = path.join(process.cwd(), 'docs/screenshots/phase-1-3-fix');
  fs.mkdirSync(outDir, { recursive: true });

  for (const theme of themes) {
    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // Bisection failure (no sign change: x^2 + 1 on [0, 2])
      try {
        await page.goto('http://localhost:5173/methods/bisection', { timeout: 6000 });
        await page.evaluate((t) => {
          localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute('data-theme', t);
        }, theme);
        await page.reload();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

        // Fill inputs: func = x^2 + 1, a = 0, b = 2
        const funcInput = page.locator('input[name="function"], input').first();
        if (await funcInput.isVisible()) {
          await funcInput.fill('x^2 + 1');
        }
        const aInput = page.locator('input[name="a"]');
        if (await aInput.isVisible()) {
          await aInput.fill('0');
        }
        const bInput = page.locator('input[name="b"]');
        if (await bInput.isVisible()) {
          await bInput.fill('2');
        }

        const solveBtn = page.locator('button[type="submit"]', { hasText: 'Solve' });
        if (await solveBtn.isVisible()) {
          await solveBtn.click();
          await page.waitForTimeout(800);
          await page.screenshot({ path: path.join(outDir, `bisection-failure-${theme}-${vp.name}.png`), fullPage: true });
        }
      } catch (e) {
        console.error(`Bisection failure ${theme} ${vp.name} error:`, e.message);
      }

      // Gauss-Seidel divergence
      try {
        await page.goto('http://localhost:5173/methods/gauss_seidel', { timeout: 6000 });
        await page.evaluate((t) => {
          localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
          document.documentElement.setAttribute('data-theme', t);
        }, theme);
        await page.reload();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

        const solveGs = page.locator('button[type="submit"]', { hasText: 'Solve' });
        if (await solveGs.isVisible()) {
          await solveGs.click();
          await page.waitForTimeout(800);
          await page.screenshot({ path: path.join(outDir, `gauss-seidel-divergence-${theme}-${vp.name}.png`), fullPage: true });
        }
      } catch (e) {
        console.error(`Gauss-Seidel divergence ${theme} ${vp.name} error:`, e.message);
      }
    }
  }

  await browser.close();
  console.log('Failure screenshots completed.');
})();
