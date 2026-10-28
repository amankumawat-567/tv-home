# Focus navigation (scope stack)

How `frontend/src/focus/engine.ts` and `state/nav.ts` keep Back/Home behaving
correctly as panels open on top of each other — the PRD's own rule: "Back
always goes up one level, Home always returns to Home, and focus returns to
whatever opened a panel."

Each box is a focus *scope*; arrow keys only ever move within the current
(top) scope. Opening a panel pushes a scope and remembers which element had
focus; Back pops it and restores that focus exactly.

```mermaid
stateDiagram-v2
    [*] --> root: app loads

    root: Home / Apps tab
    quickSettings: Quick Settings panel
    settingsShell: Settings shell (list + detail)
    appStore: App Store
    keyboard: On-screen keyboard
    confirm: Confirm dialog
    tileOptions: Tile options (hold OK)

    root --> quickSettings: Menu / hold Home /\nselect a status icon
    quickSettings --> settingsShell: select a tile
    settingsShell --> settingsShell: pick a different\ncategory (no scope push —\nlateral, not deeper)
    settingsShell --> keyboard: focus a text field\n(e.g. Wi-Fi password)
    root --> appStore: select the App Store tile
    appStore --> keyboard: Add a website

    root --> tileOptions: hold OK on a banner
    tileOptions --> confirm: Remove

    quickSettings --> root: Back (closes panel)
    settingsShell --> quickSettings: Back
    keyboard --> settingsShell: Back (hold) / Done
    appStore --> root: Back
    tileOptions --> root: Back / Cancel
    confirm --> tileOptions: Back / Cancel

    root --> root: Home key, from anywhere —\nunwinds every open scope\nand closes any running app
```

A tap of Back pops one scope; a *held* Back is only special-cased inside the
keyboard (it closes the keyboard instead of deleting a character) — see
`components/OnScreenKeyboard.tsx`.
