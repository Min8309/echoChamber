// Adapted from Pixel Agents 1.5.0, Copyright (c) 2026 Pablo De Lucca.
// SPDX-License-Identifier: MIT. See /assets/pixel-agents/LICENSE.txt.
const MAX_DELTA_TIME_SEC = 0.05;

export function startGameLoop(canvas, callbacks) {
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;

  let lastTime = 0;
  let rafId = 0;
  let stopped = false;

  const frame = (time) => {
    if (stopped) return;
    const dt =
      lastTime === 0
        ? 0
        : Math.min((time - lastTime) / 1000, MAX_DELTA_TIME_SEC);
    lastTime = time;

    callbacks.update(dt);

    ctx.imageSmoothingEnabled = false;
    callbacks.render(ctx);

    rafId = requestAnimationFrame(frame);
  };

  rafId = requestAnimationFrame(frame);

  return () => {
    stopped = true;
    cancelAnimationFrame(rafId);
  };
}
