import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const viewports = [320, 360, 375, 390, 430, 768, 820, 1024, 1280, 1440, 1920];
const pages = [
  ["home", "/"],
  ["chapter", "/chapters/ch1_nonlinear"],
  ["method", "/methods/bisection"],
  ["method-matrix", "/methods/gauss_seidel"],
  ["about", "/about"],
  ["notfound", "/nope"],
];

const browser = await chromium.launch();
const issues = [];

for (const width of viewports) {
  const height = width < 768 ? 844 : 900;
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  page.on("pageerror", (error) => issues.push(`${width} pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") issues.push(`${width} console: ${message.text()}`);
  });

  for (const [name, path] of pages) {
    await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(300);
    const result = await page.evaluate(() => {
      const root = document.documentElement;
      const overflow = root.scrollWidth - window.innerWidth;
      const offenders = [];
      for (const el of document.querySelectorAll("body *")) {
        const style = getComputedStyle(el);
        if (style.position === "fixed" || style.position === "sticky") continue;
        if (style.display === "none" || style.visibility === "hidden") continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        if (rect.right > window.innerWidth + 1.5 || rect.left < -1.5) {
          // ignore descendants of an intentional horizontal scroller
          let parent = el.parentElement;
          let scroller = false;
          while (parent) {
            const ps = getComputedStyle(parent);
            if (["auto", "scroll"].includes(ps.overflowX)) { scroller = true; break; }
            parent = parent.parentElement;
          }
          if (scroller) continue;
          offenders.push({
            tag: el.tagName.toLowerCase(),
            cls: String(el.className).slice(0, 110),
            text: (el.textContent ?? "").trim().slice(0, 50),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
          });
        }
      }
      return { overflow, offenders: offenders.slice(0, 8) };
    });
    if (result.overflow > 1 || result.offenders.length) {
      issues.push(`${width} ${name}: overflow=${result.overflow} ${JSON.stringify(result.offenders)}`);
    }
    await page.screenshot({ path: `/tmp/nms-audit/${name}-${width}.png`, fullPage: false });
  }
  await context.close();
}

await browser.close();
console.log(issues.length ? issues.join("\n") : "No overflow issues found");
