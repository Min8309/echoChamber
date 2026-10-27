import { findPath } from "./pixel-agents/pathfinding.js";

export const TILE = 32,
  COLS = 24,
  ROWS = 18;
export const WIDTH = TILE * COLS,
  HEIGHT = TILE * ROWS;
export const PLACES = [
  { name: "카페 테라스", col: 7, row: 8 },
  { name: "도서관 앞", col: 16, row: 8 },
  { name: "중앙 광장", col: 11, row: 13 },
];
export function makeMap() {
  return Array.from({ length: ROWS }, (_, row) =>
    Array.from({ length: COLS }, (_, col) =>
      ((row >= 8 && row <= 9 && col >= 1 && col <= 22) ||
        (col >= 11 && col <= 12 && row >= 2 && row <= 16) ||
        (row >= 8 && row <= 12 && col >= 9 && col <= 14)) &&
      !(col === 12 && row === 10)
        ? 1
        : 0,
    ),
  );
}
export function createResidents(agents) {
  return agents.map((agent, index) => ({
    agent,
    index,
    col: PLACES[index % 3].col,
    row: PLACES[index % 3].row,
    x: PLACES[index % 3].col,
    y: PLACES[index % 3].row,
    path: [],
    frame: 0,
    direction: "down",
  }));
}
export function planMeeting(residents, event, map) {
  const speaker = residents.find((r) => r.agent.agent_id === event.speaker_id);
  const listener = residents.find(
    (r) => r.agent.agent_id === event.listener_id,
  );
  if (!speaker || !listener) return false;
  const place = PLACES[(event.step - 1) % PLACES.length];
  for (const [resident, offset] of [
    [speaker, 0],
    [listener, 1],
  ]) {
    // Snap only unfinished movement on replay reset, never cross blocked tiles.
    resident.col = Math.round(resident.x);
    resident.row = Math.round(resident.y);
    resident.x = resident.col;
    resident.y = resident.row;
    resident.path = findPath(
      resident.col,
      resident.row,
      place.col + offset,
      place.row,
      map,
      new Set(),
    );
  }
  return true;
}
export function advanceResidents(residents, dt) {
  for (const resident of residents) {
    let remaining = dt * 5;
    while (remaining > 0 && resident.path.length) {
      const target = resident.path[0],
        dx = target.col - resident.x,
        dy = target.row - resident.y;
      const distance = Math.hypot(dx, dy);
      resident.direction =
        Math.abs(dx) > Math.abs(dy)
          ? dx < 0
            ? "left"
            : "right"
          : dy < 0
            ? "up"
            : "down";
      resident.frame += dt * 8;
      if (distance <= remaining) {
        resident.x = target.col;
        resident.y = target.row;
        resident.col = target.col;
        resident.row = target.row;
        resident.path.shift();
        remaining -= distance;
      } else {
        resident.x += (dx / distance) * remaining;
        resident.y += (dy / distance) * remaining;
        remaining = 0;
      }
    }
  }
}

function label(ctx, text, x, y, color = "#f7edcd", size = 12) {
  ctx.fillStyle = color;
  ctx.font = `bold ${size}px monospace`;
  ctx.textAlign = "center";
  ctx.fillText(text, x, y);
}
function tree(ctx, x, y, size = 1) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(size, size);
  ctx.fillStyle = "#2a543447";
  ctx.fillRect(-20, 8, 47, 18);
  ctx.fillStyle = "#745237";
  ctx.fillRect(-5, -7, 10, 30);
  ctx.fillStyle = "#285740";
  ctx.fillRect(-23, -34, 46, 38);
  ctx.fillRect(-15, -46, 30, 56);
  ctx.fillStyle = "#44844d";
  ctx.fillRect(-23, -36, 35, 29);
  ctx.fillRect(-13, -47, 23, 34);
  ctx.fillStyle = "#6c9b4e";
  ctx.fillRect(-13, -42, 18, 11);
  ctx.fillRect(-21, -28, 11, 10);
  ctx.restore();
}
function building(ctx, x, y, w, h, name, roof) {
  ctx.fillStyle = "#294d3d44";
  ctx.fillRect(x + 8, y + 12, w + 12, h + 18);
  ctx.fillStyle = "#9a7950";
  ctx.fillRect(x, y, w, h);
  ctx.fillStyle = "#e3c395";
  ctx.fillRect(x + 5, y + 5, w - 10, h - 10);
  ctx.fillStyle = "#ba9567";
  for (let row = y + 8; row < y + h; row += 14) {
    ctx.fillRect(x, row, w, 2);
  }
  ctx.fillStyle = "#6f4d37";
  ctx.fillRect(x, y + h - 8, w, 8);
  ctx.fillRect(x + 6, y, 6, h);
  ctx.fillRect(x + w - 12, y, 6, h);
  for (let wx = x + 21; wx < x + w - 20; wx += 43) {
    ctx.fillStyle = "#76543c";
    ctx.fillRect(wx - 3, y + 22, 28, 37);
    ctx.fillStyle = "#83b8b1";
    ctx.fillRect(wx, y + 25, 22, 29);
    ctx.fillStyle = "#e8d9a6";
    ctx.fillRect(wx + 10, y + 25, 2, 29);
    ctx.fillRect(wx, y + 39, 22, 2);
  }
  ctx.fillStyle = "#624a36";
  ctx.fillRect(x + w / 2 - 13, y + h - 44, 26, 39);
  ctx.fillStyle = "#b18c5e";
  ctx.fillRect(x + w / 2 - 9, y + h - 39, 18, 34);
  for (let row = 0; row < 40; row += 5) {
    const inset = (40 - row) * 0.55;
    ctx.fillStyle = row % 10 === 0 ? roof : "#7f503e";
    ctx.fillRect(x - 12 + inset, y - 40 + row, w + 24 - inset * 2, 6);
  }
  ctx.fillStyle = "#613f30";
  ctx.fillRect(x - 12, y, w + 24, 7);
  ctx.fillStyle = "#5b4638";
  ctx.fillRect(x + 13, y + 7, w - 26, 17);
  label(ctx, name, x + w / 2, y + 20, "#fff0c6", 10);
}
export function makeTownBackground() {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = "#89ac67";
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  for (let row = 0; row < ROWS; row++)
    for (let col = 0; col < COLS; col++) {
      ctx.fillStyle = (row * 11 + col * 7) % 3 === 0 ? "#96b872" : "#83a761";
      ctx.fillRect(col * TILE, row * TILE, TILE, TILE);
      if ((row + col) % 4 === 0) {
        ctx.fillStyle = "#6d9857";
        ctx.fillRect(col * TILE + 7, row * TILE + 9, 3, 5);
        ctx.fillRect(col * TILE + 11, row * TILE + 13, 3, 3);
      }
    }
  const map = makeMap();
  for (let row = 0; row < ROWS; row++)
    for (let col = 0; col < COLS; col++)
      if (map[row][col]) {
        ctx.fillStyle = (row + col) % 2 ? "#cbbd99" : "#d5c9aa";
        ctx.fillRect(col * TILE, row * TILE, TILE, TILE);
        ctx.strokeStyle = "#acaa8d";
        ctx.strokeRect(col * TILE + 0.5, row * TILE + 0.5, TILE - 1, TILE - 1);
        ctx.fillStyle = "#b6af94";
        ctx.fillRect(col * TILE + 9, row * TILE + 12, 10, 3);
      }
  building(ctx, 50, 128, 168, 115, "HOBBS CAFE", "#bc694a");
  ctx.fillStyle = "#f1d5a6";
  ctx.fillRect(47, 199, 175, 10);
  for (let x = 48; x < 220; x += 20) {
    ctx.fillStyle = "#b9483b";
    ctx.fillRect(x, 199, 10, 10);
  }
  building(ctx, 510, 104, 195, 130, "SMALLVILLE LIBRARY", "#536e79");
  building(ctx, 544, 390, 158, 118, "TOWN HALL", "#b67d50");
  building(ctx, 55, 382, 159, 91, "NEIGHBORHOOD", "#798b86");
  // Town gateway and fountain are actual scene objects, not screenshot overlays.
  ctx.fillStyle = "#765b3d";
  ctx.fillRect(339, 28, 9, 57);
  ctx.fillRect(421, 28, 9, 57);
  ctx.fillRect(331, 22, 107, 20);
  label(ctx, "SMALLVILLE", 384, 37, "#fff0c6", 12);
  const fx = 12.5 * TILE,
    fy = 10.5 * TILE;
  ctx.fillStyle = "#777f75";
  ctx.fillRect(fx - 25, fy - 17, 50, 34);
  ctx.fillStyle = "#d4d9bc";
  ctx.fillRect(fx - 22, fy - 21, 44, 34);
  ctx.fillStyle = "#6fb2bf";
  ctx.fillRect(fx - 17, fy - 17, 34, 25);
  ctx.fillStyle = "#edf4df";
  ctx.fillRect(fx - 5, fy - 31, 10, 28);
  ctx.fillRect(fx - 11, fy - 26, 22, 6);
  for (const [x, y, s] of [
    [26, 80, 1.3],
    [250, 87, 1.3],
    [470, 103, 1.1],
    [739, 105, 1.4],
    [265, 218, 1],
    [485, 243, 1],
    [39, 347, 1.1],
    [253, 425, 1.2],
    [485, 500, 1.3],
    [733, 362, 1.2],
    [41, 548, 1.1],
    [738, 547, 1.3],
    [285, 550, 0.9],
  ])
    tree(ctx, x, y, s);
  for (const [x, y] of [
    [252, 300],
    [480, 301],
    [290, 420],
    [457, 424],
  ]) {
    ctx.fillStyle = "#604a36";
    ctx.fillRect(x, y, 35, 7);
    ctx.fillRect(x + 4, y + 7, 4, 13);
    ctx.fillRect(x + 27, y + 7, 4, 13);
  }
  for (let x = 65; x < 705; x += 64) {
    ctx.fillStyle = "#708d53";
    ctx.fillRect(x, 558, 40, 6);
    ctx.fillStyle = "#ebc17a";
    ctx.fillRect(x + 5, 552, 4, 4);
    ctx.fillStyle = "#d87972";
    ctx.fillRect(x + 24, 547, 5, 5);
  }
  label(ctx, "CAFE TERRACE", 254, 252, "#395847", 10);
  label(ctx, "LIBRARY WALK", 566, 252, "#395847", 10);
  label(ctx, "TOWN SQUARE", 382, 422, "#395847", 10);
  return canvas;
}
export function drawTown(
  ctx,
  background,
  residents,
  sprites,
  selected,
  active,
  time,
) {
  ctx.clearRect(0, 0, WIDTH, HEIGHT);
  ctx.drawImage(background, 0, 0);
  for (const resident of [...residents].sort((a, b) => a.y - b.y)) {
    const x = (resident.x + 0.5) * TILE,
      y = (resident.y + 1) * TILE;
    ctx.fillStyle = "#26463850";
    ctx.beginPath();
    ctx.ellipse(x, y - 3, 14, 5, 0, 0, Math.PI * 2);
    ctx.fill();
    if (
      resident.agent.agent_id === selected ||
      resident.agent.agent_id === active
    ) {
      ctx.strokeStyle =
        resident.agent.agent_id === active ? "#ffe09a" : "#3366cc";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.ellipse(x, y - 3, 19, 8, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    const sprite = sprites[resident.index % 3],
      moving = resident.path.length > 0;
    const frame = moving ? [0, 1, 2, 1][Math.floor(time * 8) % 4] : 1;
    const row =
      resident.direction === "up"
        ? 1
        : ["left", "right"].includes(resident.direction)
          ? 2
          : 0;
    if (sprite?.complete && sprite.naturalWidth) {
      ctx.save();
      ctx.translate(x, y);
      if (resident.direction === "left") ctx.scale(-1, 1);
      ctx.drawImage(sprite, frame * 16, row * 32, 16, 32, -16, -64, 32, 64);
      ctx.restore();
    } else {
      ctx.fillStyle = ["#3366cc", "#0d9488", "#a16207"][resident.index % 3];
      ctx.fillRect(x - 9, y - 33, 18, 28);
      ctx.fillStyle = "#f0c9a1";
      ctx.fillRect(x - 8, y - 47, 16, 16);
    }
    const name = resident.agent.name;
    ctx.font = "bold 12px sans-serif";
    const w = ctx.measureText(name).width + 14;
    ctx.fillStyle = "#fffbedee";
    ctx.fillRect(x - w / 2, y + 3, w, 19);
    label(ctx, name, x, y + 17, "#304c3d", 12);
  }
}
