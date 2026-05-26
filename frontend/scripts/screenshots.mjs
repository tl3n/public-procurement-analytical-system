// One-shot screenshot pass over the four primary routes. Intended to be run
// inside the official mcr.microsoft.com/playwright image so no host installs
// are required.
//
//   docker run --rm \
//     -v "$PWD/frontend:/work" -w /work \
//     mcr.microsoft.com/playwright:latest \
//     node scripts/screenshots.mjs

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const BASE = process.env.BASE_URL || "http://host.docker.internal:5173";
const OUT = path.resolve("/work/screenshots");
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  locale: "uk-UA",
});
const page = await ctx.newPage();

async function shoot(slug, url, waitSelector) {
  const target = BASE + url;
  console.log("→", slug, target);
  await page.goto(target, { waitUntil: "domcontentloaded", timeout: 30000 });
  if (waitSelector) {
    try {
      await page.waitForSelector(waitSelector, { timeout: 15000 });
    } catch (err) {
      console.warn(`waitSelector "${waitSelector}" timed out:`, err.message);
    }
  }
  // Give Recharts SVGs + Manrope swap + react-query transitions a beat.
  await page.waitForTimeout(1200);
  await page.screenshot({
    path: path.join(OUT, `${slug}.png`),
    fullPage: true,
  });
  console.log("✓", slug);
}

await shoot("01-dashboard", "/", "main");
await shoot("02-tenders", "/tenders", "table tbody tr");

// Pick a real tender id from the API so the detail page shows actual data.
let tenderId = null;
try {
  const res = await fetch(`${BASE}/api/tenders?limit=1`);
  const json = await res.json();
  tenderId = json?.data?.[0]?.id ?? null;
} catch (err) {
  console.warn("could not fetch tender id:", err.message);
}
if (tenderId) {
  await shoot("03-tender-detail", `/tenders/${tenderId}`, "main");
} else {
  console.warn("no tender id available, skipping detail screenshot");
}

await shoot("04-statistics", "/statistics", "main");

await browser.close();
console.log("done →", OUT);
