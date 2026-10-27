import React, { useEffect, useRef, useState } from "react";
import { startGameLoop } from "./village/pixel-agents/gameLoop.js";
import {
  WIDTH,
  HEIGHT,
  PLACES,
  makeMap,
  createResidents,
  planMeeting,
  advanceResidents,
  makeTownBackground,
  drawTown,
} from "./village/town.js";

export default function VillageScene({ agents, run, busy, names }) {
  const panel = useRef(null),
    canvas = useRef(null),
    world = useRef(null);
  const events = useRef([]),
    running = useRef(true),
    selected = useRef(null),
    receiving = useRef(false);
  events.current = run?.events || [];
  receiving.current = busy;
  const [playing, setPlaying] = useState(true),
    [restart, setRestart] = useState(0);
  const [selectedId, setSelectedId] = useState(null),
    [index, setIndex] = useState(-1);
  const [phase, setPhase] = useState("idle"),
    [positions, setPositions] = useState({});
  const [expanded, setExpanded] = useState(false),
    [spritesReady, setSpritesReady] = useState(false);
  running.current = playing;
  selected.current = selectedId;
  const rosterKey = agents.map((agent) => agent.agent_id).join("|");

  useEffect(() => {
    const onFullscreen = () => {
      if (!document.fullscreenElement) setExpanded(false);
    };
    const onEscape = (event) => {
      if (event.key === "Escape" && !document.fullscreenElement)
        setExpanded(false);
    };
    document.addEventListener("keydown", onEscape);
    document.addEventListener("fullscreenchange", onFullscreen);
    return () => {
      document.removeEventListener("keydown", onEscape);
      document.removeEventListener("fullscreenchange", onFullscreen);
    };
  }, []);

  useEffect(() => {
    if (!canvas.current || !agents.length) return;
    let disposed = false;
    const residents = createResidents(agents),
      map = makeMap(),
      background = makeTownBackground();
    const state = {
      residents,
      map,
      index: -1,
      phase: "idle",
      elapsed: 0,
      clock: 0,
      snapshot: 0,
      active: null,
    };
    world.current = state;
    setIndex(-1);
    setPhase("idle");
    setPlaying(true);
    running.current = true;
    setSelectedId((previous) =>
      agents.some((agent) => agent.agent_id === previous)
        ? previous
        : agents[0].agent_id,
    );
    setSpritesReady(false);
    const sprites = [0, 1, 2].map((number) => {
      const image = new Image();
      image.src = `/assets/pixel-agents/char_${number}.png`;
      return image;
    });
    Promise.all(sprites.map((image) => image.decode().catch(() => null))).then(
      () => {
        if (!disposed)
          setSpritesReady(sprites.every((image) => image.naturalWidth > 0));
      },
    );
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const stop = startGameLoop(canvas.current, {
      update(dt) {
        if (document.hidden) return;
        state.clock += dt;
        if (running.current) {
          if (
            state.phase === "idle" &&
            state.index + 1 < events.current.length
          ) {
            state.index += 1;
            state.active = events.current[state.index];
            planMeeting(residents, state.active, map);
            state.phase = "walk";
            state.elapsed = 0;
            setIndex(state.index);
            setPhase("walk");
          }
          if (state.phase === "walk") {
            if (reducedMotion)
              for (const resident of residents) {
                const target = resident.path.at(-1);
                if (target) {
                  resident.x = resident.col = target.col;
                  resident.y = resident.row = target.row;
                  resident.path = [];
                }
              }
            else advanceResidents(residents, dt);
            if (residents.every((resident) => !resident.path.length)) {
              state.phase = "talk";
              state.elapsed = 0;
              setPhase("talk");
            }
          } else if (state.phase === "talk") {
            state.elapsed += dt;
            if (state.elapsed >= 3) {
              state.phase = "idle";
              setPhase("idle");
            }
          } else if (
            state.index >= 0 &&
            state.index + 1 === events.current.length &&
            !receiving.current
          ) {
            setPhase("complete");
            setPlaying(false);
            running.current = false;
          }
        }
        state.snapshot += dt;
        if (state.snapshot >= 0.25) {
          state.snapshot = 0;
          setPositions(
            Object.fromEntries(
              residents.map((resident) => [
                resident.agent.agent_id,
                { x: resident.x.toFixed(2), y: resident.y.toFixed(2) },
              ]),
            ),
          );
        }
      },
      render(ctx) {
        drawTown(
          ctx,
          background,
          residents,
          sprites,
          selected.current,
          state.active?.speaker_id,
          state.clock,
        );
      },
    });
    return () => {
      disposed = true;
      stop();
      world.current = null;
    };
  }, [run?.run_id, rosterKey, restart]);

  function selectFromCanvas(event) {
    const rect = canvas.current.getBoundingClientRect();
    const x = ((event.clientX - rect.left) * WIDTH) / rect.width,
      y = ((event.clientY - rect.top) * HEIGHT) / rect.height;
    const resident = world.current?.residents.find(
      (item) =>
        Math.abs((item.x + 0.5) * 32 - x) < 24 &&
        Math.abs((item.y + 1) * 32 - 30 - y) < 35,
    );
    if (resident) setSelectedId(resident.agent.agent_id);
  }
  async function toggleExpand() {
    if (expanded) {
      if (document.fullscreenElement) await document.exitFullscreen();
      setExpanded(false);
    } else {
      try {
        await panel.current.requestFullscreen();
      } catch {
        /* Responsive expanded fallback for browsers without fullscreen. */
      }
      setExpanded(true);
    }
  }
  const current = run?.events[index];
  const agent = agents.find((item) => item.agent_id === selectedId);
  const status = busy
    ? "실험 수신 중"
    : run?.pending
      ? "미저장 기록 재생"
      : run
        ? "저장 기록 재생"
        : "마을 대기";
  return (
    <section
      ref={panel}
      className={`panel village-panel ${expanded ? "is-expanded" : ""}`}
      aria-labelledby="village-title"
    >
      <div className="section-heading">
        <div>
          <h2 id="village-title">Smallville Live Environment</h2>
          <p className="village-subtitle">
            Pixel Agents 캐릭터 · 카페 / 도서관 / 광장
          </p>
        </div>
        <span className="village-state">{status}</span>
      </div>
      {run?.source_data && (
        <div className="village-source">
          <strong>
            실제 {run.source_data.source === "review" ? "리뷰" : "댓글"}에서
            시작 · {run.source_data.title}
          </strong>
          {run.source_data.discussion ? (
            <>
              <p>
                자료 {run.source_data.rows.length}건 · {run.agents.length}인
                토론 · 원문 묶음을 함께 검토합니다.
              </p>
              <details>
                <summary>선택한 실제 자료 보기</summary>
                {run.source_data.rows.map((row) => (
                  <p key={row.row_id}>
                    자료 {row.number}: {row.text}
                  </p>
                ))}
              </details>
            </>
          ) : (
            <p>원문: {run.source_data.text}</p>
          )}
          {run.source_data.analysis ? (
            <small>
              실험 시작 당시 원문 AI 분석:{" "}
              {run.source_data.analysis.is_gossip ? "가십" : "일반 내용"} · 감정{" "}
              {run.source_data.analysis.sentiment} · 평판 영향{" "}
              {run.source_data.analysis.reputation_impact}
            </small>
          ) : (
            <small>
              실험 시작 당시 원문 AI 의미 분석 없음 · 기초 수치로 비교할 수
              있습니다.
            </small>
          )}
        </div>
      )}
      <div className="village-stage interactive-town">
        <canvas
          ref={canvas}
          width={WIDTH}
          height={HEIGHT}
          onClick={selectFromCanvas}
          role="img"
          aria-label={`실제 에이전트 ${agents.length}명이 이동하는 Smallville 마을. 아래 버튼으로 캐릭터를 선택할 수 있습니다.`}
          data-sprites-ready={spritesReady}
          data-phase={phase}
          data-step={current?.step || 0}
        />
        <div className="town-location-tags">
          {PLACES.map((place) => (
            <span key={place.name}>{place.name}</span>
          ))}
        </div>
        {current && phase === "talk" && (
          <div className="town-speech" role="status">
            <strong>
              {names[current.speaker_id]} → {names[current.listener_id]}
            </strong>
            <p>{current.utterance}</p>
          </div>
        )}
      </div>
      <div className="village-playback">
        <span>
          {current
            ? `STEP ${current.step}/${run.events.length} · ${phase === "walk" ? "대화 장소로 이동 중" : phase === "talk" ? "대화 중" : phase === "complete" ? "재생 완료" : "다음 대화 대기"}`
            : "실험을 실행하면 이동과 대화가 시작됩니다"}
        </span>
        <div>
          <button
            type="button"
            disabled={!run?.events.length || phase === "complete"}
            onClick={() => setPlaying((value) => !value)}
          >
            {playing ? "일시정지" : "계속 재생"}
          </button>
          <button
            type="button"
            disabled={!run?.events.length}
            onClick={() => setRestart((value) => value + 1)}
          >
            처음부터 재생
          </button>
        </div>
      </div>
      <div className="village-agents" aria-label="마을 캐릭터 선택">
        {agents.map((resident, i) => (
          <button
            key={resident.agent_id}
            type="button"
            aria-pressed={selectedId === resident.agent_id}
            aria-label={`${resident.name} 캐릭터 선택`}
            onClick={() => setSelectedId(resident.agent_id)}
            data-position={
              positions[resident.agent_id]
                ? `${positions[resident.agent_id].x},${positions[resident.agent_id].y}`
                : "initial"
            }
          >
            <i className={`avatar color-${i % 3}`}>{resident.name[0]}</i>
            {resident.name}
          </button>
        ))}
      </div>
      {agent && (
        <div className="resident-detail">
          <strong>
            {agent.name} · {agent.occupation}
          </strong>
          <p>{agent.current_goal}</p>
          <small>기본 활동 장소: {agent.current_location}</small>
        </div>
      )}
      <div className="village-current">
        <span>
          {current
            ? `실제 실행 기록 · STEP ${current.step}`
            : "첫 이야기를 기다리고 있습니다"}
        </span>
        <p>
          {current?.utterance ||
            "캐릭터를 누르거나 실험을 시작해 보세요. 이동은 실제 대화 순서를 지도 위에서 재현합니다."}
        </p>
      </div>
      <div className="village-footer">
        <a
          href="/assets/pixel-agents/LICENSE.txt"
          target="_blank"
          rel="noreferrer"
        >
          Pixel Agents · MIT / 저작권 고지
        </a>
        <button type="button" className="village-expand" onClick={toggleExpand}>
          {expanded ? "확대 닫기 ×" : "마을 공간 확대 ↗"}
        </button>
      </div>
    </section>
  );
}
