const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const themes = ['light', 'paper', 'dark'];
  const dump = {};

  for (const theme of themes) {
    dump[theme] = {};
    await page.goto('http://localhost:5173/methods/bisection');
    await page.evaluate((t) => {
      localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
      document.documentElement.setAttribute('data-theme', t);
    }, theme);
    await page.reload();
    await page.waitForLoadState('networkidle').catch(() => {});

    dump[theme].chip = await page.evaluate(() => {
      const el = document.querySelector('[class*="badge"], [class*="chip"], span');
      const s = window.getComputedStyle(el);
      return { borderColor: s.borderColor, borderRadius: s.borderRadius, backgroundColor: s.backgroundColor, color: s.color, boxShadow: s.boxShadow };
    });

    dump[theme].tabs = await page.evaluate(() => {
      const el = document.querySelector('[role="tablist"]');
      const s = window.getComputedStyle(el);
      return { borderColor: s.borderColor, borderRadius: s.borderRadius, backgroundColor: s.backgroundColor, color: s.color, boxShadow: s.boxShadow };
    });

    dump[theme].emptyState = await page.evaluate(() => {
      const el = document.querySelector('section, [class*="empty"]');
      const s = window.getComputedStyle(el);
      return { borderColor: s.borderColor, borderRadius: s.borderRadius, backgroundColor: s.backgroundColor, color: s.color, boxShadow: s.boxShadow };
    });

    dump[theme].inputPanel = await page.evaluate(() => {
      const el = document.querySelector('form, section');
      const s = window.getComputedStyle(el);
      return { borderColor: s.borderColor, borderRadius: s.borderRadius, backgroundColor: s.backgroundColor, color: s.color, boxShadow: s.boxShadow };
    });

    dump[theme].card = await page.evaluate(() => {
      const el = document.querySelector('.rounded-lg, section');
      const s = window.getComputedStyle(el);
      return { borderColor: s.borderColor, borderRadius: s.borderRadius, backgroundColor: s.backgroundColor, color: s.color, boxShadow: s.boxShadow };
    });
  }

  fs.writeFileSync(path.join(process.cwd(), 'docs/computed-styles-dump.json'), JSON.stringify(dump, null, 2));
  console.log('Computed styles dumped successfully.');
  await browser.close();
})();
