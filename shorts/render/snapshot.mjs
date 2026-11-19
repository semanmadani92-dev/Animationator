// Screenshot a page from the local server once it sets window.__ready.
// Usage: node render/snapshot.mjs <url> <out.png>
import { createRequire } from "node:module";

// Playwright is preinstalled globally; CommonJS resolution finds it via NODE_PATH.
const { chromium } = createRequire(import.meta.url)("playwright");

const [url, out] = process.argv.slice(2);
const browser = await chromium.launch({
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on("console", (m) => m.type() === "error" && console.error("page:", m.text()));
page.on("pageerror", (e) => console.error("pageerror:", e.message));
await page.goto(url);
await page.waitForFunction(() => window.__ready === true, null, { timeout: 120000 });
await page.screenshot({ path: out });
await browser.close();
console.log("saved", out);
