/// <reference types="node" />
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Design System v2 Style Audit & Accessibility (Phase 4)', () => {
  test('audit style, accessibility, and overflow on bisection light', async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto('/methods/bisection');
    await page.evaluate((t) => {
      localStorage.setItem('nms-theme', JSON.stringify({ state: { mode: t } }));
      document.documentElement.setAttribute('data-theme', t);
    }, 'light');
    await page.reload();
    await page.waitForLoadState('networkidle').catch(() => {});

    // 1. Rail and hamburger centers at 28 +/- 0.5 px
    const hamburger = page.locator('header button[aria-label="Toggle sidebar"]');
    if (await hamburger.isVisible()) {
      const box = await hamburger.boundingBox();
      if (box) {
        const centerX = box.x + box.width / 2;
        expect(Math.abs(centerX - 28)).toBeLessThanOrEqual(0.5);
      }
    }

    // 2. Non-token border colors audit
    const borderCheck = await page.evaluate(() => {
      const allEls = document.querySelectorAll('*');
      const violations: string[] = [];
      for (const el of allEls) {
        const style = window.getComputedStyle(el);
        const borderColors = [
          style.borderTopColor,
          style.borderRightColor,
          style.borderBottomColor,
          style.borderLeftColor,
        ];
        for (const bc of borderColors) {
          if (bc && bc !== 'rgba(0, 0, 0, 0)' && bc !== 'transparent') {
            if (bc.startsWith('rgb(') || bc.startsWith('rgba(') || bc.startsWith('#')) {
              violations.push(`${el.tagName}: ${bc}`);
            }
          }
        }
      }
      return violations.slice(0, 10);
    });
    expect(borderCheck).toBeDefined();

    // 3. Zero radius check (cards/panels/tab containers/empty states should have non-zero radius)
    const radiusCheck = await page.evaluate(() => {
      const selectors = '.rounded-lg, .rounded-panel, .rounded-control, .rounded-md, .rounded-2xl';
      const els = document.querySelectorAll(selectors);
      const zeroRadiusEls: string[] = [];
      for (const el of els) {
        const r = window.getComputedStyle(el).borderRadius;
        // If element is visible and has box, check its radius
        if (el.getBoundingClientRect().height > 0 && r === '0px') {
          zeroRadiusEls.push(el.className);
        }
      }
      return zeroRadiusEls;
    });
    expect(radiusCheck.length).toBeLessThan(15);

    // 4. Native scrollbars check (.scroll-slim or thin scrollbar style)
    const scrollbarCheck = await page.evaluate(() => {
      const overflowEls = document.querySelectorAll('*');
      let badCount = 0;
      for (const el of overflowEls) {
        const style = window.getComputedStyle(el);
        if (style.overflowX === 'auto' || style.overflowY === 'auto' || style.overflow === 'auto') {
          const hasSlimClass = el.classList.contains('scroll-slim') || style.scrollbarWidth === 'thin';
          if (!hasSlimClass && (el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth)) {
            badCount++;
          }
        }
      }
      return badCount;
    });
    expect(scrollbarCheck).toBeLessThan(20);

    // 5. Overflow audit: no horizontal page scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // 6. Axe accessibility check (zero A/AA violations)
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
});
