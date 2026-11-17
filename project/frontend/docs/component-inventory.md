# Component inventory

> **How this was derived.** The source prototype was a minified React bundle.
> The original component names, file structure and prop names were **not
> recoverable** — the inventory below is a *behavioural reconstruction* of the
> 25 components found in the bundle, not recovered source. What *was* preserved
> verbatim is the set of CSS class names, which is the styling contract.
>
> The advisor module that existed in the bundle was deliberately dropped: it
> was unreachable from the prototype's own UI (the mode switch only ever
> exposed "Family app" and "Design system").

## Shared UI atoms — `src/components/ui/`

| Component | Responsibility | Reusable | Dependencies | Location |
|---|---|---|---|---|
| `Icon` | Renders a named inline SVG path; always `aria-hidden` | Yes | — | `ui/Icon.tsx` |
| `Button` | `variant` / `size` / `icon` / `iconRight` / `block` | Yes | `Icon` | `ui/Button.tsx` |
| `Card` | Surface; renders as `<button>` when interactive | Yes | — | `ui/Card.tsx` |
| `Chip` | Status pill with an optional icon | Yes | `Icon` | `ui/Chip.tsx` |
| `DemoTag` | Marks content as sample data | Yes | — | `ui/DemoTag.tsx` |
| `Eyebrow` | Uppercase micro-label | Yes | — | `ui/Eyebrow.tsx` |
| `ScoreRing` | SVG gauge showing a score out of 100 | Yes | — | `ui/ScoreRing.tsx` |
| `SegmentedControl` | `role="tablist"` group of mutually exclusive options | Yes | `Icon` | `ui/SegmentedControl.tsx` |
| `StatusIcon` | Round glyph encoding a milestone status | Yes | `Icon` | `ui/StatusIcon.tsx` |
| `Toggle` | Checkbox rendered as a switch | Yes | — | `ui/Toggle.tsx` |
| `STATUS_META` | Status → `{ label, tone }` lookup | — | — | `ui/statusMeta.ts` |
| `ICON_PATHS` | The 32 inline SVG paths, typed as `IconName` | — | — | `ui/iconPaths.ts` |

## Brand — `src/components/brand/`

| Component | Responsibility | Reusable | Dependencies | Location |
|---|---|---|---|---|
| `BrandMark` | Blue rounded-square logo placeholder | Yes | — | `brand/BrandMark.tsx` |
| `Wordmark` | Brand mark plus "My"/"Sherpas" | Yes | `BrandMark` | `brand/Wordmark.tsx` |

## Charts — `src/components/charts/`

| Component | Responsibility | Reusable | Dependencies | Location |
|---|---|---|---|---|
| `CashDebtBars` | Cash against card balance, one shared scale | Yes | — | `charts/CashDebtBars.tsx` |
| `GoalTimeline` | Three-point timeline across a household's goals | Yes | — | `charts/GoalTimeline.tsx` |
| `TwoGoals` | Two goals competing for the same money | Yes | — | `charts/TwoGoals.tsx` |
| `PlanChart` | Dispatches to the chart a recommendation calls for | Yes | the above, `ScoreRing` | `charts/PlanChart.tsx` |

## Family app — `src/features/family/components/`

| Component | Responsibility | Reusable | Dependencies | Location |
|---|---|---|---|---|
| `PhoneFrame` | iPhone chrome, scroll container, screen tint | Yes | `PhoneStatusBar` | `family/components/phone/PhoneFrame.tsx` |
| `PhoneStatusBar` | The 9:41 status bar | Yes | — | `family/components/phone/PhoneStatusBar.tsx` |
| `ScreenHeader` | Top bar: optional back, title, optional action | Yes | `Icon` | `family/components/ScreenHeader.tsx` |
| `TabBar` | Four-item bottom navigation | Yes | `Icon` | `family/components/TabBar.tsx` |
| `WelcomeScreen` | Screen 1 — greeting, plan link, value props, CTA | No | `Button`, `Icon`, `Wordmark` | `family/components/WelcomeScreen.tsx` |
| `StoryScreen` | Screen 2 — the animated storyboard player | No | `Button`, `Icon`, `Eyebrow`, `Wordmark` | `family/components/StoryScreen.tsx` |
| `HomeDashboard` | Screen 3 — score, priority, next step, journey, CTA | No | `Card`, `ScoreRing`, `Button`, `Icon` | `family/components/HomeDashboard.tsx` |
| `PlanScreen` | Screen 5 — section pills and recommendation cards | No | `PlanRecommendation`, `DemoTag` | `family/components/PlanScreen.tsx` |
| `PlanRecommendation` | Collapsible what/why/next recommendation with a chart | Yes | `Card`, `PlanChart`, `Button` | `family/components/PlanRecommendation.tsx` |
| `ProgressScreen` | Screen 6/8 — milestones and journey tabs | No | `SegmentedControl`, `MilestoneItem`, `Card` | `family/components/ProgressScreen.tsx` |
| `MilestoneItem` | Timeline milestone row with a status setter | Yes | `StatusIcon`, `Chip`, `Button` | `family/components/MilestoneItem.tsx` |
| `CheckInScreen` | Screen 7 — the seven-step monthly check-in | No | `Button`, `Toggle`, `Icon`, `Card` | `family/components/CheckInScreen.tsx` |
| `MentorScreen` | Screen 4 — voice mentor, transcript, controls | No | `VoiceOrb`, `Button`, `Icon`, `DemoTag` | `family/components/MentorScreen.tsx` |
| `VoiceOrb` | Animated orb showing the voice state | Yes | `Icon` | `family/components/VoiceOrb.tsx` |

## Design system — `src/features/design-system/`

| Component | Responsibility | Reusable | Dependencies | Location |
|---|---|---|---|---|
| `DesignSystemPage` | The design-system reference page shell and its intro | No | the sections below | `design-system/DesignSystemPage.tsx` |
| `ColorSection` | Colour tokens and the surface gradients | No | `ColorSwatch` | `design-system/sections/ColorSection.tsx` |
| `TypographySection` | The type scale | No | `Eyebrow` | `design-system/sections/TypographySection.tsx` |
| `LayoutSection` | Spacing, radii and elevation | No | — | `design-system/sections/LayoutSection.tsx` |
| `ComponentsSection` | Buttons, cards, status, inputs, navigation | No | most atoms | `design-system/sections/ComponentsSection.tsx` |
| `DataSection` | Financial charts and voice-interaction states | No | `Card`, `ScoreRing`, charts | `design-system/sections/DataSection.tsx` |
| `ColorSwatch` | Token chip, name and value | Yes | — | `design-system/ColorSwatch.tsx` |
| `ApproxBadge` | Marks an approximated value | Yes | — | `design-system/ApproxBadge.tsx` |

## Shell and state

| Item | Responsibility | Location |
|---|---|---|
| `App` | Root: the shell's mode | `app/App.tsx` |
| `AppShell` | The prototype bar and the three-column stage | `app/AppShell.tsx` |
| `JourneyRail` | The left-hand rail that drives the phone | `app/JourneyRail.tsx` |
| `FamilyPhone` | The phone mockup and the screen routing | `app/FamilyPhone.tsx` |
| `PrototypeControls` | Household summary, voice states, sample conversation, reset | `app/PrototypeControls.tsx` |
| `ErrorBoundary` | Keeps a render error from blanking the app | `app/ErrorBoundary.tsx` |
| `FamilyProvider` | Owns all family-app state | `family/state/FamilyProvider.tsx` |
| `MentorProvider` | Owns the mentor conversation and voice machine | `family/state/MentorProvider.tsx` |
| `familyReducer` | Every state transition, as a pure function | `family/state/familyReducer.ts` |
| `selectors` | Milestones joined with their status; completed/pending/current | `family/state/selectors.ts` |
| `useFamilyData` / `useNavigation` | Context hooks | `family/state/useFamily.ts` |
| `useMentorSession` | Mentor context hook | `family/state/useMentorSession.ts` |
| `useTypewriter` | Word-by-word reveal | `family/hooks/useTypewriter.ts` |
| `askMentor` | Typed client for the live mentor | `family/services/mentorApi.ts` |
| `greetingFor` | Hour → "Good morning/afternoon/evening" | `family/utils/greeting.ts` |

## Constraints the implementation keeps

- No component exceeds 250 lines. The largest file in `src/` is
  `features/family/data/families.ts`, which is data rather than a component.
- No file contains minified code.
- No `any` in the codebase.
- No duplicated UI: every screen uses the shared atoms above.
- Domain state lives in the reducer, not in component `useState`.
