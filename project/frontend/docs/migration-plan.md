# Migration plan and verification report

Migration of `project/frontend/reference/prototype.html` into this React + Vite
project.

**Status: complete.** Every phase below was executed. The original HTML file was
not modified.

---

## Source analysis

| | |
|---|---|
| Source | `project/frontend/reference/prototype.html` — 275 KB, 634 lines |
| `<style>` | 48.9 KB, 16 commented sections, 430 CSS rules, 290 classes |
| `<script>` | 225.7 KB IIFE bundle: React 18.3.1 production + ~87 KB of app code |
| Markup | `<body><div id="root"></div></body>` — no static markup, no SSR |
| Network | One Google Fonts stylesheet (Inter). Nothing else. |
| Assets | No images. 32 icons and the logo are inline SVG paths. |
| State | Entirely in-memory React state. No storage, no persistence. |
| Components | 25 React components recovered from the minified bundle |

### What the application does

A prototype shell with two areas: a **family app** (seven screens inside a
phone mockup) and a **design system** reference page. A journey rail on the
left drives the phone through eight steps; a control panel on the right offers
a voice-state picker, a sample conversation and a reset.

---

## Phases

| Phase | Delivered |
|---|---|
| 1 — Foundation | Scaffold cleaned; document head replaced; brand favicon; CSS split into 14 layers (verified rule-for-rule identical to the source); 12 shared UI atoms; 2 brand components. |
| 2 — Domain, data, state | 20 domain types; the four households transcribed verbatim; six lookup tables; a pure reducer covering every transition; two contexts; a selector layer. |
| 3 — Feature components | 4 charts, 14 family-app components, 3 design-system components. |
| 4 — Shell integration | `App`, `AppShell`, `ErrorBoundary`, `prototypeModes`; feature and responsive CSS. |
| 5 — Live mentor (frontend) | Typed API client, env-driven configuration, a mentor session provider that owns the conversation and the seven voice states, and conditional UI so the app never claims a live answer it does not have. |
| 6 — Quality assurance | Typecheck, lint, production build, pixel diff, text diff, 48 interaction assertions, console check. |
| 7 — Documentation | This file, `architecture.md`, `component-inventory.md`, `scripts/README.md`, and the project README. |

### Deliberate omissions

- **The advisor module was dropped.** It existed in the bundle but was
  unreachable from the prototype's own UI — the mode switch only ever exposed
  "Family app" and "Design system". Carrying it forward would have preserved
  roughly 500 lines of code with no entry point.
- **No router.** The prototype is a phone application with no deep links and
  no browser-back navigation. Adding React Router would have changed that and
  added a dependency for no requirement.
- **No test-runner dependency.** The verification tooling is dependency-free
  (see below). A Tier-2 decision on Vitest + Testing Library is still open.

---

## Verification

All checks were run against the **production build** served by `vite preview`.

### Static checks

| Check | Command | Result |
|---|---|---|
| Types | `pnpm typecheck` | 0 errors |
| Lint | `pnpm lint` | 0 errors, 0 warnings |
| Build | `pnpm build` | 299 kB raw / 89.6 kB gzipped |

### Visual parity

`scripts/compare.mjs` decodes both screenshots in the browser's own canvas and
diffs them pixel by pixel (tolerance 8/255).

| Screen | Differing pixels |
|---|---|
| Welcome | **0.000 %** |
| Design system | **0.000 %** |
| Home dashboard | **0.000 %** |
| Financial story | 0.002 % — the chapter progress bar, one 50 ms animation tick |
| My financial plan | **0.000 %** |
| Goals & milestones | **0.000 %** |
| Progress overview | **0.000 %** |
| Check-in | **0.000 %** |
| AI mentor | **0.000 %** |
| Mentor speaking | **0.000 %** |
| Responsive, 1100 px | **0.000 %** |
| Responsive, 760 px | 0.015 % — the animated waveform bars, CSS animation phase |

Eleven of twelve screens are **pixel-identical**. The one that differs does so
only in a continuously animating element, where two captures can never agree to
the byte.

### Text parity

`scripts/textdiff.mjs` extracts the visible text of every screen from both
applications and compares them line by line.

```
welcome          text identical (43 lines)
home             text identical (69 lines)
story            text identical (46 lines)
plan             text identical (57 lines)
milestones       text identical (54 lines)
journey          text identical (57 lines)
checkin          text identical (42 lines)
mentor           text identical (54 lines)
design-system    text identical (150 lines)

All screens have identical visible text.
```

This check caught two real defects during the migration: typographic
apostrophes (`’`) had been substituted for the prototype's straight ones, and
one line read "How's calculated" instead of "How it's calculated".

### Behaviour parity

`scripts/behaviour.mjs` drives a real browser through 48 assertions covering
navigation, the plan, the progress screen, the full check-in flow, the mentor's
voice machine, the prototype controls and the design-system page.

**The identical script passes against both the original prototype and the
migration: 48 passed, 0 failed in each.** That is the strongest available
evidence of behavioural equivalence.

### Console

No errors, warnings or unhandled exceptions across every screen, in the
production build.

### Mentor code paths

| Configuration | Result |
|---|---|
| `VITE_MENTOR_API_URL` unset | Fully scripted. **Zero network requests** — verified by intercepting `fetch`. |
| URL set, backend unreachable, `VITE_MENTOR_FALLBACK=scripted` | Falls back to the scripted answer; the conversation badge reads "Sample". |
| URL set, backend unreachable, `VITE_MENTOR_FALLBACK=error` | Shows the mentor's error state with "Try again" and "Read my plan". |

The live path itself — a successful answer from the backend — is **not
verified**, because the backend is not part of this phase. See "Remaining
work".

---

## Known differences from the original

| # | Difference | Why |
|---|---|---|
| 1 | The story's chapter strip has `role="group"`. | A `div` with an `aria-label` and no role is ignored by assistive technology. Invisible, strictly better. |
| 2 | Interactive `Card`s carry an explicit `type="button"`. | The prototype relied on the default. There are no `<form>` elements, so behaviour is unchanged. |
| 3 | The mentor's badge reads "Live" instead of "Sample" when the answer really came from the backend. | The original always said "Sample", which would have been untrue. |
| 4 | The prototype-controls note reads differently when the live mentor is enabled. | The original said "Voice is simulated"; that would have been untrue. |
| 5 | The React version is 19.3.1 rather than 18.3.1, and the app runs under `StrictMode`. | The target project's stack. The prototype was not in `StrictMode`; the scaffold is. Effects were audited and cleaned up accordingly. |
| 6 | Two ARIA imperfections from the prototype were left alone: `role="tab"` without a `tabpanel`, and `span`s styled as buttons in the design-system tab-bar demo. | Fixing them would change behaviour. Documented rather than silently altered. |

## Remaining work

1. **Live mentor end-to-end.** The frontend half is complete and its three
   code paths are verified. The backend half is out of scope for this phase
   and has known defects: its proxy base URL is missing the `/v1` suffix, its
   model (`gpt-4o-mini`) is not in the proxy's model table, and its MCP call
   guesses a protocol the server does not speak. The README recommends
   reading the case JSON from `cases/` instead, which never expires.
2. **Tier-2 testing.** The decision on Vitest + Testing Library is still open.
   The dependency-free tooling covers behaviour and appearance; unit tests for
   the reducer and the selectors would add regression safety at the cost of
   four dev dependencies.
3. **Brand tokens.** Several colour and type values are marked `APPROX.` in
   the prototype itself, because the official Sherpas assets could not be
   downloaded. They are preserved as-is and need the brand kit to correct.
