# Third-party notices

## Pixel Agents 1.5.0

Source: user-supplied `pixel-agents-main (1).zip`, upstream
https://github.com/pixel-agents-hq/pixel-agents

Copyright (c) 2026 Pablo De Lucca. Licensed under the MIT License.
The complete license is retained in `frontend/public/assets/pixel-agents/LICENSE.txt`
and is accessible from the village footer in the deployed application.

Included material:

- `webview-ui/src/office/engine/gameLoop.ts` → `frontend/src/village/pixel-agents/gameLoop.js`:
  adapted to JavaScript and the local frame-time constant.
- `webview-ui/src/office/layout/tileMap.ts` → `frontend/src/village/pixel-agents/pathfinding.js`:
  adapted to JavaScript and a simple outdoor walkability grid.
- `webview-ui/public/assets/characters/char_0.png`, `char_1.png`, `char_2.png`:
  unchanged PNG sprite sheets.

The procedural outdoor terrain/buildings, EchoChamber event playback, UI and
FastAPI integration are separate implementation work. No Claude Code provider,
terminal launcher, session scanner, extension adapter or external asset pack is included.
