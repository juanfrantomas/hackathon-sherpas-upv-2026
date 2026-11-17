# Verification tooling

Dependency-free checks that compare this application with the original
prototype at `project/frontend/reference/prototype.html`.

Node 22+ ships a global `WebSocket`, so `cdp.mjs` implements just enough of
the Chrome DevTools Protocol to drive a real browser — no Puppeteer, no
Playwright, no test runner.

`cdp.mjs` expects Chrome at `/usr/bin/google-chrome`. Override with
`CHROME_PATH=/path/to/chrome`.

## Running the checks

```bash
pnpm build
pnpm preview --port 4173 &          # serve the production build

# 1. Interactions (48 assertions)
#    Build without VITE_BACKEND_API_URL: the assertions describe the
#    application on its own demo data.  With the backend connected the
#    milestones come from the plan and the mentor answers with the AI, so the
#    texts and the number of milestones are no longer the demo ones.
pnpm verify:behaviour http://localhost:4173/

# 2. Visible text, screen by screen
pnpm verify:text \
  "file://$PWD/reference/prototype.html" \
  http://localhost:4173/

# 3. Screenshots
pnpm capture "file://$PWD/reference/prototype.html" /tmp/parity/original original
pnpm capture http://localhost:4173/ /tmp/parity/migration migration

# 4. Pixel diff
pnpm verify:parity /tmp/parity/original /tmp/parity/migration /tmp/parity/diffs
```

`verify:behaviour` and `verify:text` can be pointed at the **original**
prototype as well — the behaviour script passes identically against both, which
is what makes it evidence of equivalence rather than of plausibility.

## The scripts

| Script | What it does |
|---|---|
| `cdp.mjs` | Minimal Chrome DevTools Protocol client: navigate, evaluate, screenshot, set the viewport. |
| `capture.mjs` | Captures the twelve reference views (nine screens, two viewports and the mentor's speaking state). |
| `compare.mjs` | Decodes two PNGs in the browser's canvas and reports the percentage of differing pixels, the maximum channel delta and the rows that differ. |
| `textdiff.mjs` | Extracts the visible text of every screen from both applications and diffs it line by line. |
| `sidebyside.mjs` | Renders two screenshots side by side, cropped to a region, for inspecting a difference by eye. |

## What the pixel diff means now

The prototype is the historical source of this application, not a live
specification: the app now reads the household's milestones from the
Financial Milestones backend, and the mentor speaks with the AI. The screens
that show real data therefore no longer match the prototype, on purpose:

| Screen | Why it differs |
|---|---|
| `06-milestones`, `07-journey` | The milestones come from the backend, so there are the ones the plan really produces, plus the section that explains them. |
| `09-mentor`, `10-mentor-speaking` | The mentor can open a live voice session, which adds a control to the stage. |
| `11-responsive-1100`, `12-responsive-760` | The shell shows whether the backend is reachable, which moves the household selector. |

The screens that are still static (`01-welcome`, `02-design-system`,
`03-home`, `04-story`, `05-plan`, `08-checkin`) stay within the usual noise
of the animated elements.

## Interpreting the pixel diff

Continuously animating elements — the mentor's waveform bars, the story's
progress bar — can never agree to the byte between two captures. A difference
confined to those regions is expected; a difference anywhere else is not.
