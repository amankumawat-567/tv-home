# Design

Visual and interaction design for TV Home 2.0, as implemented in
`frontend/src/styles/`. This is the "how it looks and feels" companion to
`ARCHITECTURE.md` ("how it's built"); the product requirements behind every
choice here live in `docs/PRD.pdf`.

## Principles

- **Remote-first.** Every screen is built and tested by arrow keys, Enter and
  Back alone — a mouse is never required and a keyboard only stands in for a
  remote during development. See "Focus and navigation" below.
- **Dark, calm, low-motion.** The Pentium G620 this runs on has no CPU to
  spare on decorative animation; see "Motion" below.
- **One font, one type scale, one grid.** Consistency over novelty — the
  tokens in `tokens.css` are the only sizes/colours anything should use.

## Layout

Designed at 1920×1080 and scaled by viewport height, so 1366×768 (today's
monitor) and any future 1080p display render the same relative layout:

```css
:root {
  font-size: 1.85vh; /* ≈20px at 1080p — the base unit everything else is a multiple of */
}
```

- **Safe area:** 5% margin on every side (`--safe-x`, `--safe-y`), so nothing
  critical sits at the literal edge of the screen.
- **Grid:** 12 columns; app banners span 2 columns each, so 5–6 fit per row
  with the next one peeking in at the edge (`.grid-12` in `components.css`).

## Colour tokens

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#101418` | Page background |
| `--surface` | `#1B2028` | Panels, cards, the keyboard |
| `--surface-raised` | `#262C36` | Focused list rows, pressed buttons |
| `--text` | `#F1F3F5` | Primary text |
| `--text-muted` | `#A9B1BC` | Secondary text, row titles |
| `--accent` | `#FFB547` | App Store tile, selected toggles, progress |
| `--good` | `#6FDCB8` | Connected, on |
| `--warn` | `#F5C451` | Weak signal, clock not synced |
| `--bad` | `#FF8A80` | Errors, the Shut down button |

## Type scale

Font: **Lexend**, bundled locally via `@fontsource/lexend` (fallback: Ubuntu,
sans-serif) — chosen for TV legibility and shipped as local files so the UI
never depends on the network for its own chrome.

| Role | Size @ 1080p | Token | Weight |
|---|---|---|---|
| Clock (top bar) | 34px | `--text-clock` | 400 |
| Screen title | 44px | `--text-title` | 700 |
| Row title | 26px | `--text-row` | 500 |
| Body, list rows | 24px | `--text-body` | 400 |
| Labels, captions | 20px (the floor — nothing smaller) | `--text-label` | 500 |

## Components

- **App banner:** 16:9, rounded corners, the app's icon centred on a colour
  sampled from the icon's own edge pixels (`utils/brandColor.ts` — averages a
  ring of edge pixels via an offscreen canvas, falling back to a stable
  hash-based colour when there's no icon yet). The name only appears under
  the banner when it's focused, keeping unfocused rows visually quiet.
- **Status icons:** real Material Symbols path data, bundled inline
  (`components/Icons.tsx`) — fetched once from the `@material-symbols/svg-400`
  npm package (Apache 2.0), no runtime network dependency. `WifiIcon` is the
  one hand-drawn exception: it renders 0–4 bars from live signal strength,
  which no static glyph can represent.
- **Buttons:** pill-shaped; unfocused = surface fill, focused = white fill
  with dark text (see `.focusable.is-focused` for the shared focus treatment
  every interactive element uses).
- **Settings list rows:** full width, ~64px tall at 1080p, label left, value
  right (`components/SettingsRow.tsx`) — the one row shape every Settings
  page (Wi-Fi, Bluetooth, Sound, …) is built from.

## Focus and navigation

- **Focused tile:** scales to 1.1×, gets a 3px white outline and a soft
  shadow, 150ms ease-out — see `--focus-scale`/`--focus-outline`/`--focus-ease`
  in `tokens.css`. `prefers-reduced-motion` drops the transition to 0ms.
- **Focused row/list item:** colour change only, no scale — lists stay
  visually steady while scrolling through them (`.settings-row`,
  `.top-tab`).
- The engine (`frontend/src/focus/engine.ts`) always scrolls the newly
  focused element fully into view and never lets it sit under the safe
  margin.
- A **scope stack** backs every overlay (Quick Settings, a Settings page, the
  App Store, a confirm dialog, the on-screen keyboard): opening one narrows
  what arrow keys can reach, and Back always unwinds exactly one level,
  restoring focus to whatever opened it. See
  `docs/diagrams/focus-navigation.md` for the state diagram and
  `state/nav.ts` for the code that drives it.

## Motion

- **No looping animation on Home** — it costs CPU on the Pentium with nothing
  gained. The only animations are the ~150ms focus transition and the launch
  screen's spinner, both of which stop under `prefers-reduced-motion`.
- Panels (Quick Settings, the on-screen keyboard) slide in; nothing pulses,
  shimmers, or auto-plays.

## Known gaps vs. the PRD's visual spec

- The on-screen wireframe/architecture images embedded in the PRD doc weren't
  pixel-matched against the implementation; the layout here follows the PRD's
  *written* spec (screen map, grid, type scale) rather than a visual diff
  against those images.
