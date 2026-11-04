import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await page.waitForTimeout(400);

const report = await page.evaluate(() => {
  function info(el) {
    if (!el) return null;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      text: (el.textContent ?? "").trim().slice(0, 60),
      tag: el.tagName,
      color: s.color,
      background: s.backgroundColor,
      bgImage: s.backgroundImage !== "none" ? s.backgroundImage.slice(0, 80) : "none",
      border: s.borderColor,
      radius: s.borderRadius,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      width: Math.round(r.width),
      height: Math.round(r.height),
    };
  }
  const headings = [...document.querySelectorAll("h1,h2,h3")].map(info);
  const sections = [...document.querySelectorAll("section")].slice(0, 10).map(info);
  const buttons = [...document.querySelectorAll("a[class*=btn],button")].slice(0, 14).map(info);
  return { headings, sections, buttons };
});
console.log(JSON.stringify(report, null, 2));

// Closing CTA (last section) styles
const cta = await page.evaluate(() => {
  const sections = [...document.querySelectorAll("section")];
  const s = sections[sections.length - 1];
  const h2 = s.querySelector("h2");
  const p = s.querySelector("p");
  const style = getComputedStyle(s);
  return {
    sectionBg: style.backgroundColor,
    sectionText: style.color,
    h2Color: getComputedStyle(h2).color,
    pColor: getComputedStyle(p).color,
    html: s.outerHTML.slice(0, 400),
  };
});
console.log("CTA", JSON.stringify(cta, null, 2));

await browser.close();
