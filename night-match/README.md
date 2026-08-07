# Night Match

A number-matching puzzle built for a dark room — the kind of game you play
one-handed while sitting next to a kid who is nearly asleep.

Same game as the pencil-and-paper puzzle variously called Take Ten, Seeds, or
Numberama, and the same mechanic as the mobile *Number Match* games: clear the
board by matching pairs that are equal or that add up to ten.

This is an independent implementation, not a reskin of anyone's app. No ads, no
timers, no accounts, no network calls of any kind.

## Why it looks like this

Most "dark modes" are blue-grey, which is the wrong end of the spectrum for a
bedroom. Everything here is warm and low-blue: a brown-biased near-black ground
(`#14110E`), parchment numerals, and a single ember accent (`#E39B3C`). Nothing
on screen goes above 185/255 luminance — there is no white surface anywhere, and
no bright flash when a pair clears. Matched tiles warm to ember and then cool
back into the dark.

The main control is a **dimmer**, not a light/dark toggle:

| Level | Ground | For |
| --- | --- | --- |
| Dusk | `#1C1813` | A room with a nightlight on |
| Night | `#14110E` | Default — lights out |
| Blackout | `#000000` | True black; on OLED the dark pixels are genuinely off |

The app deliberately stays dark regardless of the system theme. Being dark is
the point of it.

## Rules

- **Match** two numbers that are **equal** or that **add up to ten**.
- **Reach** — tiles count as adjacent across, down, diagonally, or from the end
  of one row to the start of the next. Already-cleared tiles do not block the
  path between two numbers.
- **Rows** — a row that empties out is removed and everything below shifts up.
- **Add** appends every remaining number to the end of the board, in reading
  order. Unlimited, so there is never anything to wait for or watch.

Scoring is 10 per pair, 50 per cleared row, 200 for clearing the board.

Diagonal matching can be switched off in the help panel (tap the wordmark) if
you prefer the stricter variant.

## Running it

It is one self-contained HTML file with no build step and no dependencies:

```
open index.html
```

To install it on a phone, serve the folder over HTTPS and use **Add to Home
Screen**. The service worker caches the shell, so after the first load it runs
with no network at all:

```
python3 -m http.server 8000
```

Your game, score, and dimmer setting are kept in `localStorage`, so closing the
app mid-game — which happens a lot at bedtime — loses nothing.

## Tests

`tests/` holds two suites, both run against the shipped `index.html` rather than
a copy, so they cannot drift from it:

```
cd tests
npm install
npm test
```

- `rules.test.mjs` extracts the rule functions out of `index.html` and checks
  the matching, adjacency, wrap, diagonal-edge, and row-collapse logic (26
  assertions).
- `e2e.mjs` drives the real page in Chromium: tapping, matching, undo, add,
  hint, row collapse, the win panel, dimmer levels, persistence, mobile
  overflow, and a luminance sweep asserting nothing on screen is near-white.
