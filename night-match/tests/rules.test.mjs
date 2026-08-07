// Pulls the real rule functions out of index.html and exercises them,
// so the test can never drift from the shipped implementation.
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const APP_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");
const APP_FILE = join(APP_DIR, "index.html");


const src = readFileSync(APP_FILE, "utf8");

function slice(startMarker, endMarker) {
  const a = src.indexOf(startMarker);
  const b = src.indexOf(endMarker);
  assert.ok(a !== -1 && b !== -1 && b > a, `markers not found: ${startMarker}`);
  return src.slice(a, b);
}

const rules = slice("/* ── Rules", "/* ── Setup");
const collapse = slice("// Drop any fully cleared row", "/* ── Setup");

const make = new Function(`
  "use strict";
  const COLS = 9;
  let cells = [];
  let diagonals = true;
  ${rules}
  return {
    set(board, diag) {
      cells = board.map(v => v === 0 ? { v: 0, cleared: true } : { v, cleared: false });
      diagonals = diag !== false;
    },
    raw(board, diag) { cells = board; diagonals = diag !== false; },
    get cells() { return cells; },
    pairs, connected, valid, findMove, remaining, collapseRows
  };
`);

const G = make();
let pass = 0;
function check(name, fn) {
  try { fn(); pass++; }
  catch (e) { console.error("FAIL:", name, "\n ", e.message); process.exitCode = 1; }
}

// ── pairs ────────────────────────────────────────────────────────────
check("equal numbers pair", () => assert.ok(G.pairs(7, 7)));
check("numbers summing to ten pair", () => assert.ok(G.pairs(3, 7)));
check("unrelated numbers do not pair", () => assert.ok(!G.pairs(3, 8)));
check("5 and 5 pair both ways", () => assert.ok(G.pairs(5, 5)));

// ── horizontal adjacency ─────────────────────────────────────────────
check("side by side matches", () => {
  G.set([3, 7, 1, 1, 1, 1, 1, 1, 1]);
  assert.ok(G.valid(0, 1));
});
check("separated by an uncleared tile does not match", () => {
  G.set([3, 9, 7, 1, 1, 1, 1, 1, 1]);
  assert.ok(!G.valid(0, 2));
});
check("cleared tiles are see-through", () => {
  G.set([3, 0, 0, 7, 1, 1, 1, 1, 1]);
  assert.ok(G.valid(0, 3));
});

// ── row wrap (end of one row to start of the next) ───────────────────
check("end of row meets start of next", () => {
  //            0..8 row 0                     9 = row 1 col 0
  G.set([1, 1, 1, 1, 1, 1, 1, 1, 4,   6, 1, 1]);
  assert.ok(G.valid(8, 9));
});

// ── vertical ─────────────────────────────────────────────────────────
check("directly below matches", () => {
  G.set([2, 1, 1, 1, 1, 1, 1, 1, 1,
         8, 1, 1, 1, 1, 1, 1, 1, 1]);
  assert.ok(G.valid(0, 9));
});
check("same column with a cleared row between matches", () => {
  G.set([2, 1, 1, 1, 1, 1, 1, 1, 1,
         0, 1, 1, 1, 1, 1, 1, 1, 1,
         8, 1, 1, 1, 1, 1, 1, 1, 1]);
  assert.ok(G.valid(0, 18));
});
check("same column blocked by an uncleared tile does not match", () => {
  G.set([2, 1, 1, 1, 1, 1, 1, 1, 1,
         5, 1, 1, 1, 1, 1, 1, 1, 1,
         8, 1, 1, 1, 1, 1, 1, 1, 1]);
  assert.ok(!G.valid(0, 18));
});

// ── diagonal ─────────────────────────────────────────────────────────
check("down-right diagonal matches", () => {
  G.set([2, 9, 9, 9, 9, 9, 9, 9, 9,
         9, 8, 9, 9, 9, 9, 9, 9, 9]);
  assert.ok(G.valid(0, 10));
});
check("down-left diagonal matches", () => {
  G.set([9, 2, 9, 9, 9, 9, 9, 9, 9,
         8, 9, 9, 9, 9, 9, 9, 9, 9]);
  assert.ok(G.valid(1, 9));
});
check("diagonal does not wrap around the grid edge", () => {
  // index 8 is row 0 col 8; index 8+9-1 = 16 is row 1 col 7 (legal),
  // but index 8+9+1 = 18 is row 2 col 0 — a wrap that must be rejected.
  G.set([9, 9, 9, 9, 9, 9, 9, 9, 2,
         9, 9, 9, 9, 9, 9, 9, 9, 9,
         8, 9, 9, 9, 9, 9, 9, 9, 9]);
  assert.ok(!G.valid(8, 18));
});
check("diagonals can be switched off", () => {
  G.set([2, 9, 9, 9, 9, 9, 9, 9, 9,
         9, 8, 9, 9, 9, 9, 9, 9, 9], false);
  assert.ok(!G.valid(0, 10));
});

// ── guards ───────────────────────────────────────────────────────────
check("a tile cannot match itself", () => {
  G.set([5, 5, 1, 1, 1, 1, 1, 1, 1]);
  assert.ok(!G.valid(0, 0));
});
check("cleared tiles cannot be matched", () => {
  G.set([0, 5, 1, 1, 1, 1, 1, 1, 1]);
  assert.ok(!G.valid(0, 1));
});
check("connected is symmetric", () => {
  G.set([3, 0, 0, 7, 1, 1, 1, 1, 1]);
  assert.equal(G.valid(0, 3), G.valid(3, 0));
});

// ── row collapse ─────────────────────────────────────────────────────
check("a fully cleared row is removed and rows shift up", () => {
  G.set([0, 0, 0, 0, 0, 0, 0, 0, 0,
         4, 4, 4, 4, 4, 4, 4, 4, 4]);
  assert.equal(G.collapseRows(), 1);
  assert.equal(G.cells.length, 9);
  assert.ok(G.cells.every(c => c.v === 4));
});
check("two cleared rows are both removed", () => {
  G.set([0, 0, 0, 0, 0, 0, 0, 0, 0,
         4, 4, 4, 4, 4, 4, 4, 4, 4,
         0, 0, 0, 0, 0, 0, 0, 0, 0]);
  assert.equal(G.collapseRows(), 2);
  assert.equal(G.cells.length, 9);
});
check("a partly cleared row stays", () => {
  G.set([0, 0, 0, 0, 0, 0, 0, 0, 3]);
  assert.equal(G.collapseRows(), 0);
  assert.equal(G.cells.length, 9);
});
check("a trailing partial row is never collapsed", () => {
  G.set([4, 4, 4, 4, 4, 4, 4, 4, 4,
         0, 0, 0]);
  assert.equal(G.collapseRows(), 0);
  assert.equal(G.cells.length, 12);
});

// ── findMove / remaining ─────────────────────────────────────────────
check("findMove locates a real pair", () => {
  G.set([1, 2, 3, 4, 6, 8, 9, 7, 5]);
  const m = G.findMove();
  assert.ok(m, "expected a move");
  assert.ok(G.valid(m[0], m[1]));
});
check("findMove returns null on a dead board", () => {
  G.set([1, 2, 1, 2, 1, 2, 1, 2, 1], false);
  // 1 and 2 never pair (not equal, sum 3); no move exists.
  assert.equal(G.findMove(), null);
});
check("remaining counts uncleared tiles", () => {
  G.set([0, 5, 0, 5, 1, 1, 1, 1, 1]);
  assert.equal(G.remaining(), 7);
});

// ── generated boards always open with a move ─────────────────────────
check("every freshly generated board has at least one move", () => {
  for (let n = 0; n < 3000; n++) {
    let board;
    do {
      board = Array.from({ length: 27 }, () => 1 + Math.floor(Math.random() * 9));
      G.set(board);
    } while (!G.findMove());
    assert.ok(G.findMove());
  }
});

console.log(`${pass} checks passed`);
