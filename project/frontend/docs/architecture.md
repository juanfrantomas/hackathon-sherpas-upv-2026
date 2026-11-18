# Architecture

MySherpas is a family-facing companion to a Sherpas financial plan. This
document describes the architecture of the Vite + React application in
`project/frontend`, which was migrated from the single-file prototype at
`project/frontend/reference/prototype.html`.

## What the application is

A prototype shell with two areas:

- **Family app** — a phone mockup containing a seven-screen companion for a
  household: welcome → financial story → dashboard → plan → progress →
  monthly check-in → voice mentor.
- **Design system** — a reference page documenting the tokens, typography,
  components, charts and voice states.

The shell also carries a journey rail (eight steps that drive the phone) and a
panel of prototype controls (voice-state picker, sample conversation, reset).

## Layers

```
app/          shell: mode switch, prototype bar, journey rail, phone, controls
components/   shared UI atoms, brand marks, charts
features/     family app, design system — each with its own data, state and styles
styles/       global layers: tokens, base, shared components, shell, phone, responsive
```

The shell is split into `AppShell` (the bar and the stage), `JourneyRail`,
`FamilyPhone` (the phone and the screen routing) and `PrototypeControls`, so
that no file carries more than one reason to change.

Dependencies point inwards: `app` → `features` → `components` → `styles`.
Features never import from `app`.

### Why feature-based rather than a flat component tree

The application has one domain (a household's plan) presented through two very
different surfaces (a phone app and a documentation page). A feature-based
layout keeps everything about "the household" — its data, its state, its
screens, its styles — inside `features/family/`, and leaves `components/` for
things that genuinely have no domain meaning, such as a button or a score ring.

There is no `services/`, `hooks/`, `types/` or `utils/` folder at the root of
`src/`: every hook, type and utility in this application belongs to exactly
one feature, so a root-level folder for them would only add indirection. The
one exception is `features/family/services/`, which exists because the mentor
talks to an external service.

## State management

**React `useReducer` plus two contexts. No state library.**

The prototype kept roughly a dozen `useState` values in its root component and
threaded them down through props. That was the prototype's largest
maintainability problem, and replacing it is the main structural change in this
migration.

`features/family/state/familyReducer.ts` holds every state transition as a
pure function of `(state, action)`:

| Action | Effect |
|---|---|
| `select_family` | Switch household; reset the view, navigation and voice state |
| `reset_all` | Restore every household's demo state and return to the welcome screen |
| `set_milestone_status` | Change one milestone's status |
| `complete_milestone` | Mark a milestone complete |
| `commit_checkin` | Commit a check-in: record, review request, shared items, milestone promotion |
| `mark_watched` | Record that the household watched their financial story |
| `navigate` | Move to a screen, merging the navigation options |
| `set_nav` / `set_voice` | Update navigation or the mentor's voice state |

Two contexts are published from one provider so that a navigation change does
not re-render every screen:

- `FamilyDataContext` — the household, its demo state, its milestones with
  their current status, and `dispatch`.
- `NavigationContext` — the current screen, the navigation options, the voice
  state, and `go()`.

`features/family/state/MentorProvider.tsx` sits on top and owns the mentor
conversation: which question is in play, which answer is being spoken, and the
transitions between the seven voice states. It is separate from the provider
because it is the only part of the application that performs I/O.

### Derived state is computed, not stored

Milestones are stored as `{ id: status }` and joined with the household's
milestone definitions by `features/family/state/selectors.ts`. `completed`,
`pending` and `current` are derived with `useMemo` rather than kept in their
own state, so they can never disagree with the source of truth.

## Navigation

**No router.** The prototype is a phone application, not a set of URL-addressed
pages: it has no deep links, and the browser back button does not navigate.
Adding React Router would have changed that behaviour and added a dependency
for no requirement.

Navigation is a typed function:

```ts
go('plan', { section: 'debt', card: 'd1' })
go('progress', { tab: 'milestones', open: 'w1' })
go('mentor', { from: 'home', topic: 'Credit card debt' })
```

The reducer merges these options into the navigation state exactly as the
prototype did, including the rule that entering the mentor resets the voice
state and remembers where to return to.

## Styling

Plain CSS with custom properties. No Tailwind, no CSS-in-JS, no CSS Modules.

The prototype already *was* a token-based design system: `:root` custom
properties for colour, type, spacing, radii, shadows and motion, plus
BEM-style class names. Re-expressing that in a utility framework would have
been a redesign, not a migration.

- `src/styles/tokens.css` — the design tokens, copied verbatim from the
  prototype, including its note that several values are approximations.
- `src/styles/base.css` — element defaults, type helpers and layout utilities.
- `src/styles/components.css` — the shared atoms.
- `src/styles/shell.css`, `src/styles/phone.css` — the prototype shell.
- `src/features/*/styles/*.css` — feature styles, imported by the feature.
- `src/styles/responsive.css` — the two breakpoints (≤1100 px, ≤760 px).

`src/styles/index.css` declares the import order, which reproduces the
prototype's cascade exactly. All class names are preserved verbatim: they are
the styling contract and the strongest surviving evidence of the original
design intent.

## Data

`features/family/data/` holds the four demo households and the small lookup
tables that go with them. Every figure and every line of copy is transcribed
verbatim from the prototype bundle. It is a curated projection of the plan data
in `cases/` at the repository root — **do not recompute these numbers**; if the
underlying plan changes, that is a deliberate, separate change.

`features/family/types.ts` holds the domain types. The compiler runs with
`erasableSyntaxOnly`, so the codebase uses union types and `as const` lookup
maps rather than enums.

## The live mentor

The prototype's mentor was entirely simulated: a scripted question and answer
per household, typed out word by word. The frontend supports the same
behaviour and can additionally ask a real backend.

```
features/family/services/config.ts      reads VITE_MENTOR_API_URL / VITE_MENTOR_FALLBACK
features/family/services/mentorApi.ts   typed client for POST /api/voice/ask
features/family/state/MentorProvider.tsx owns the conversation and the voice machine
features/family/hooks/useTypewriter.ts   word-by-word reveal used by the transcript
```

| `VITE_MENTOR_API_URL` | Behaviour |
|---|---|
| unset | Fully scripted. **No network request is made at all** and the app always works. |
| set | The mentor asks the backend. `VITE_MENTOR_FALLBACK` decides what happens if the backend cannot be reached: `scripted` (default) falls back to the scripted answer and badges the conversation "Sample"; `error` shows the mentor's error state. |

The browser never holds a credential. The team AI key stays in the backend,
which is the only component that talks to the AI proxy.

## Error handling

The prototype had exactly one error surface — the mentor's unavailable state.
It is preserved, along with its "Try again" and "Read my plan" actions.

`app/ErrorBoundary.tsx` is the one addition: it wraps the application so that a
render error shows a recoverable message instead of a blank page. It has no
effect on the happy path.

## Accessibility

The prototype's accessibility work is preserved in full: `aria-label` on every
icon button, `aria-current` on the active tab, `aria-expanded` on every
disclosure, `aria-pressed` on toggles, `aria-live` on the mentor state and the
story captions, `role="table"` semantics on tables, visible `:focus-visible`
outlines, and a global `prefers-reduced-motion` rule.

Two changes were made, both strictly additive and invisible:

- The story's chapter strip got `role="group"`, because a `div` with an
  `aria-label` and no role is ignored by assistive technology.
- The `Card` component renders a real `<button>` when it is interactive, which
  it already did in the prototype; it now carries an explicit
  `type="button"`.

Two ARIA imperfections inherited from the prototype are **not** fixed, because
fixing them would change behaviour: the segmented control uses `role="tab"`
without a corresponding `tabpanel`, and the design system's tab-bar demo uses
`span` elements styled as buttons.

## Performance

- The bundle is ~299 kB raw / ~90 kB gzipped, with no runtime dependencies
  beyond React.
- Icons are inline SVG paths, so there is no icon-font or sprite request.
- The only external request is the Inter stylesheet, loaded with `preconnect`
  and `display=swap`.
- The four households' data is one eagerly-imported module; per-household lazy
  loading was considered and rejected as complexity without measurable benefit.

## Build and tooling

Vite 8, React 19, TypeScript 7, oxlint, pnpm. No additional dependencies were
introduced by the migration.

The verification tooling under `scripts/` is deliberately **dependency-free**:
Node 22+ ships a global `WebSocket`, so a small Chrome DevTools Protocol
client (`scripts/cdp.mjs`) is enough to drive a real browser for screenshots,
pixel diffing and interaction tests. See `scripts/README.md`.
