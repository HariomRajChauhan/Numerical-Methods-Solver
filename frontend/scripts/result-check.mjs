import { chromium } from "playwright";

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.on("pageerror", (e) => console.log("PAGEERROR", e.message));
await page.goto("http://localhost:5173/methods/bisection", { waitUntil: "networkidle" });
await page.waitForTimeout(500);

// Choose first example
const options = await page.locator("#example-select option").allTextContents();
console.log("examples", options);
await page.selectOption("#example-select", { index: 1 });
await page.waitForTimeout(300);

// Solve
await page.getByRole("button", { name: "Solve", exact: true }).first().click();
await page.waitForSelector('[data-testid="result-headline"]', { timeout: 30000 });
await page.waitForTimeout(600);

const report = await page.evaluate(() => {
  function info(el) {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName,
      cls: String(el.className).slice(0, 100),
      text: (el.textContent ?? "").trim().slice(0, 60),
      color: s.color,
      background: s.backgroundColor,
      border: s.borderColor,
      radius: s.borderRadius,
      fontSize: s.fontSize,
      width: Math.round(r.width),
      height: Math.round(r.height),
    };
  }
  const sel = (q) => [...document.querySelectorAll(q)].map(info);
  return {
    badges: sel('[data-testid="result-headline"] span, [class*="rounded-pill"]'),
    headline: sel('[data-testid="result-headline"]'),
    stats: sel('[data-testid="stat-row"]'),
    summary: sel('[data-testid="result-summary"]'),
    cards: sel("section"),
    buttons: sel("button"),
  };
});
console.log(JSON.stringify(report, null, 2));

await page.screenshot({ path: "/tmp/nms-audit/bisection-solved-1440.png", fullPage: true });

// Mobile
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(500);
const mobile = await page.evaluate(() => {
  const out = [];
  for (const el of document.querySelectorAll("main *")) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && r.right > window.innerWidth + 1) {
      let p = el.parentElement, scroll = false;
      while (p) { const ps = getComputedStyle(p); if (["auto","scroll"].includes(ps.overflowX)) { scroll = true; break; } p = p.parentElement; }
      if (!scroll) out.push({ tag: el.tagName, cls: String(el.className).slice(0,80), right: Math.round(r.right), text: (el.textContent??"").trim().slice(0,40) });
    }
  }
  return { scrollWidth: document.documentElement.scrollWidth, innerWidth: innerWidth, out: out.slice(0, 20) };
});
console.log("MOBILE", JSON.stringify(mobile, null, 2));
await page.screenshot({ path: "/tmp/nms-audit/bisection-solved-390.png", fullPage: true });

await browser.close();
