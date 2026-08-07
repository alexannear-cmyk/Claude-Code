import { chromium } from "playwright";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const APP_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");
const APP_FILE = join(APP_DIR, "index.html");


const APP = "file://" + APP_FILE;
const OUT = process.env.SHOT_DIR || APP_DIR;

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || undefined,
  args: ["--no-sandbox"]
});
const ctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2
});
const page = await ctx.newPage();
await ctx.clearCookies();

const errors = [];
page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });

await page.goto(APP);
await page.waitForSelector(".tile");

// Board renders 27 tiles to start.
assert.equal(await page.locator(".tile").count(), 27, "expected 27 tiles");
assert.equal(await page.locator("#s-left").textContent(), "27");
assert.equal(await page.locator("#s-score").textContent(), "0");
console.log("✓ board renders 27 tiles");

// Play the hinted move by reading it straight out of the page state.
const move = await page.evaluate(() => findMove());
assert.ok(move, "expected an opening move");
await page.locator(`.tile[data-i="${move[0]}"]`).click();
assert.ok(
  await page.locator(`.tile[data-i="${move[0]}"]`).evaluate(n => n.classList.contains("is-selected")),
  "first tap should select"
);
console.log("✓ first tap selects");

await page.locator(`.tile[data-i="${move[1]}"]`).click();
await page.waitForTimeout(600);
assert.equal(await page.locator("#s-score").textContent(), "10", "a match scores 10");
assert.equal(await page.locator("#s-left").textContent(), "25", "two tiles come off the board");
console.log("✓ matching a pair clears two tiles and scores");

// Undo puts them back.
await page.locator("#btn-undo").click();
await page.waitForTimeout(100);
assert.equal(await page.locator("#s-score").textContent(), "0");
assert.equal(await page.locator("#s-left").textContent(), "27");
console.log("✓ undo restores the board");

// Undo is disabled once history is empty.
assert.ok(await page.locator("#btn-undo").isDisabled(), "undo should disable at the start");
console.log("✓ undo disables with no history");

// Add appends every remaining number.
await page.locator("#btn-add").click();
await page.waitForTimeout(300);
assert.equal(await page.locator(".tile").count(), 54, "add should double a full board");
assert.equal(await page.locator("#s-left").textContent(), "54");
console.log("✓ add appends the remaining numbers");

// Hint marks a genuine pair.
await page.locator("#btn-undo").click();
await page.waitForTimeout(100);
await page.locator("#btn-hint").click();
await page.waitForTimeout(100);
assert.equal(await page.locator(".tile.is-hint").count(), 2, "hint should mark exactly two tiles");
console.log("✓ hint marks a valid pair");

// An invalid pair nudges and re-picks rather than clearing anything.
await page.reload();
await page.waitForSelector(".tile");
const bad = await page.evaluate(() => {
  for (let i = 0; i < cells.length; i++)
    for (let j = i + 1; j < cells.length; j++)
      if (!valid(i, j)) return [i, j];
  return null;
});
await page.locator(`.tile[data-i="${bad[0]}"]`).click();
await page.locator(`.tile[data-i="${bad[1]}"]`).click();
await page.waitForTimeout(200);
assert.equal(await page.locator("#s-left").textContent(), "27", "an invalid pair must not clear");
assert.ok(
  await page.locator(`.tile[data-i="${bad[1]}"]`).evaluate(n => n.classList.contains("is-selected")),
  "second tap should become the new selection"
);
console.log("✓ invalid pair is rejected and re-picks");

// Row collapse: clear a whole row via the console and confirm it vanishes.
await page.evaluate(() => {
  for (let i = 0; i < 9; i++) cells[i].cleared = true;
  const removed = collapseRows();
  render();
  return removed;
});
assert.equal(await page.locator(".tile").count(), 18, "a cleared row should be removed");
console.log("✓ a cleared row collapses");

// Winning the board opens the overlay.
await page.reload();
await page.waitForSelector(".tile");
await page.evaluate(() => {
  cells.forEach(c => { c.cleared = true; });
  render();
  afterMove(0);
});
await page.waitForTimeout(200);
assert.ok(await page.locator("#overlay").evaluate(n => n.classList.contains("open")), "win overlay should open");
assert.equal(await page.locator("#ov-title").textContent(), "Board clear");
console.log("✓ clearing the board opens the win panel");

// The dimmer cycles and restyles the ground.
await page.locator("#ov-close").click();
const seen = [];
for (let i = 0; i < 3; i++) {
  seen.push(await page.evaluate(() => ({
    dim: document.documentElement.dataset.dim,
    bg: getComputedStyle(document.body).backgroundColor,
    meta: document.querySelector('meta[name="theme-color"]').content
  })));
  if (process.env.SHOT_DIR) await page.screenshot({ path: `${OUT}/dim-${seen[i].dim}.png` });
  await page.locator("#btn-dim").click();
  await page.waitForTimeout(450);
}
console.log("✓ dimmer levels:", seen.map(s => `${s.dim}=${s.bg}`).join("  "));
assert.equal(new Set(seen.map(s => s.bg)).size, 3, "each dim level needs its own ground");
assert.equal(seen.find(s => s.dim === "blackout").bg, "rgb(0, 0, 0)", "blackout must be true black");
seen.forEach(s => assert.equal(s.meta, {
  dusk: "#1C1813", night: "#14110E", blackout: "#000000"
}[s.dim], "theme-color should track the dimmer"));
console.log("✓ blackout is true #000 and theme-color follows");

// Nothing visible should be near-white at any dim level. Only fully
// opaque colours on rendered elements count.
const bright = await page.evaluate(() => {
  const RGB = /^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/;
  const hits = [];
  for (const n of document.querySelectorAll("body *")) {
    if (!n.getClientRects().length) continue;
    for (const prop of ["color", "backgroundColor", "borderTopColor"]) {
      const m = RGB.exec(getComputedStyle(n)[prop]);
      if (!m) continue;
      const alpha = m[4] === undefined ? 1 : Number(m[4]);
      if (alpha < 0.9) continue;
      const [r, g, b] = [m[1], m[2], m[3]].map(Number);
      hits.push({
        lum: 0.2126 * r + 0.7152 * g + 0.0722 * b,
        where: n.tagName.toLowerCase() + (n.id ? "#" + n.id : "." + (n.className || "")),
        prop,
        value: m[0]
      });
    }
  }
  hits.sort((a, b) => b.lum - a.lum);
  return hits.slice(0, 3);
});
console.log("  brightest:", bright.map(h => `${h.where} ${h.prop} ${h.value} (${h.lum.toFixed(0)})`).join("; "));
assert.ok(bright[0].lum < 200,
  `too bright for a dark room: ${bright[0].where} ${bright[0].prop} = ${bright[0].value}`);
console.log(`✓ peak luminance ${bright[0].lum.toFixed(0)}/255 — no white surfaces`);

// State survives a reload.
const before = await page.evaluate(() => document.documentElement.dataset.dim);
await page.reload();
await page.waitForSelector(".tile");
assert.equal(await page.evaluate(() => document.documentElement.dataset.dim), before,
  "dimmer choice should persist");
console.log(`✓ settings persist across a reload (dim=${before})`);

// Board must not scroll sideways on a phone.
const overflow = await page.evaluate(() =>
  document.documentElement.scrollWidth - document.documentElement.clientWidth);
assert.ok(overflow <= 0, `page scrolls horizontally by ${overflow}px`);
console.log("✓ no horizontal overflow at 390px");

assert.equal(errors.length, 0, "console errors:\n" + errors.join("\n"));
console.log("✓ no console errors");

await browser.close();
console.log("\nAll end-to-end checks passed.");
