import { test } from "node:test";
import assert from "node:assert/strict";
import { findPath } from "../frontend/src/village/pixel-agents/pathfinding.js";
import { startGameLoop } from "../frontend/src/village/pixel-agents/gameLoop.js";
import {
  makeMap,
  createResidents,
  planMeeting,
  advanceResidents,
  PLACES,
} from "../frontend/src/village/town.js";

test("village meeting paths avoid buildings and remain four-connected", () => {
  const map = makeMap();
  for (const start of PLACES)
    for (const end of PLACES) {
      const path = findPath(
        start.col,
        start.row,
        end.col,
        end.row,
        map,
        new Set(),
      );
      let prev = start;
      for (const tile of path) {
        assert.equal(map[tile.row][tile.col], 1);
        assert.equal(
          Math.abs(tile.col - prev.col) + Math.abs(tile.row - prev.row),
          1,
        );
        prev = tile;
      }
      assert.deepEqual(
        { col: prev.col, row: prev.row },
        { col: end.col, row: end.row },
      );
    }
  assert.deepEqual(findPath(7, 8, 2, 4, map, new Set()), []);
});

test("actual speaker and listener walk to distinct meeting positions", () => {
  const residents = createResidents(
    ["a", "b", "c"].map((agent_id) => ({ agent_id })),
  );
  const before = residents.map((r) => ({ x: r.x, y: r.y }));
  assert.ok(
    planMeeting(
      residents,
      { speaker_id: "b", listener_id: "c", step: 1 },
      makeMap(),
    ),
  );
  for (let i = 0; i < 400; i++) advanceResidents(residents, 0.05);
  assert.equal(residents[1].x, 7);
  assert.equal(residents[2].x, 8);
  assert.equal(residents[1].y, 8);
  assert.equal(residents[2].y, 8);
  assert.deepEqual({ x: residents[0].x, y: residents[0].y }, before[0]);
  assert.ok(residents.every((r) => !r.path.length));
});

test("Pixel Agents frame loop caps a resumed frame and cancels on teardown", () => {
  let frame, cancelled;
  const deltas = [];
  const originalRaf = globalThis.requestAnimationFrame,
    originalCancel = globalThis.cancelAnimationFrame;
  globalThis.requestAnimationFrame = (callback) => {
    frame = callback;
    return 42;
  };
  globalThis.cancelAnimationFrame = (id) => {
    cancelled = id;
  };
  try {
    const context = { imageSmoothingEnabled: true };
    const stop = startGameLoop(
      { getContext: () => context },
      { update: (dt) => deltas.push(dt), render: () => {} },
    );
    frame(100);
    frame(10000);
    assert.deepEqual(deltas, [0, 0.05]);
    assert.equal(context.imageSmoothingEnabled, false);
    stop();
    assert.equal(cancelled, 42);
    frame(10100);
    assert.equal(deltas.length, 2);
  } finally {
    globalThis.requestAnimationFrame = originalRaf;
    globalThis.cancelAnimationFrame = originalCancel;
  }
});
