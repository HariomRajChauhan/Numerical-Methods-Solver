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
      await page.goto('http://localhost:5173/methods/bisection');
      await page.evaluate((t) => {
        localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
        document.documentElement.setAttribute('data-theme', t);
      }, theme);
      await page.reload();
      await page.waitForLoadState('networkidle').catch(() => {});

      const solveBtn = page.locator('button[type="submit"]', { hasText: 'Solve' });
      if (await solveBtn.isVisible()) {
        await solveBtn.click();
        // Capture immediately while loading
        await page.screenshot({ path: path.join(outDir, `bisection-loading-${theme}-${vp.name}.png`), fullPage: true });
        await page.waitForTimeout(800);
      }
    }
  }

  await browser.close();
  console.log('Loading screenshots completed.');
})();
