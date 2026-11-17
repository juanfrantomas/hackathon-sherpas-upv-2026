# MySherpas — frontend

A family-facing companion to a Sherpas financial plan, migrated from the
single-file prototype at `reference/prototype.html`.

React 19 · TypeScript · Vite 8 · pnpm. No runtime dependencies beyond React.

## Run it

```bash
pnpm install
pnpm dev        # http://localhost:5173
```

```bash
pnpm build      # typecheck + production build
pnpm preview    # serve the production build
pnpm lint       # oxlint
```

## What it is

Two areas, behind a prototype shell:

- **Family app** — a phone mockup with seven screens: welcome → financial
  story → dashboard → plan → progress → monthly check-in → voice mentor.
- **Design system** — the token, type, component, chart and voice-state
  reference.

The shell carries a journey rail that drives the phone through eight steps,
and a control panel with a voice-state picker, a sample conversation and a
reset. Four demo households can be selected from the top bar.

## Configuration

The mentor runs **fully scripted** by default: it makes no network request and
always works. To ask a real backend instead, copy `.env.example` to
`.env.local` and set:

```
VITE_MENTOR_API_URL=http://localhost:8000
VITE_MENTOR_FALLBACK=scripted
```

`VITE_MENTOR_FALLBACK` decides what happens when the backend cannot be
reached: `scripted` falls back to the scripted answer and badges the
conversation "Sample"; `error` shows the mentor's error state.

The browser never holds a credential — the team AI key stays in the backend.

## Documentation

| | |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Layers, state management, navigation, styling, the mentor, accessibility |
| [docs/component-inventory.md](docs/component-inventory.md) | Every component, its responsibility and where it lives |
| [docs/migration-plan.md](docs/migration-plan.md) | What was migrated, how it was verified, and what still differs |
| [scripts/README.md](scripts/README.md) | The dependency-free verification tooling |

## Verification

`scripts/` drives a real browser through the Chrome DevTools Protocol using
only Node built-ins — no Puppeteer, no Playwright, no test runner.

```bash
pnpm build && pnpm preview --port 4173 &

pnpm verify:behaviour http://localhost:4173/          # 48 interaction assertions
pnpm verify:text <originalUrl> http://localhost:4173/ # visible text, screen by screen
pnpm verify:parity <originalDir> <migrationDir>       # pixel diff
```

The behaviour script passes identically against the original prototype and
against this application. See `docs/migration-plan.md` for the results.
