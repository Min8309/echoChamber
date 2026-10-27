import React, { useRef } from "react";

// Reuse the unchanged repository design reference. The SVG viewport shows only
// its village panel; the surrounding screenshot UI never enters the viewport.
function VillageArtwork() {
  return (
    <svg
      className="village-artwork"
      viewBox="238 297 393 298"
      role="img"
      aria-label="기존 Smallville 픽셀 아트 마을 컨셉 이미지"
    >
      <image
        href="/assets/smallville-reference.png"
        width="950"
        height="1600"
      />
    </svg>
  );
}

export default function VillageScene({ agents, run, busy, names }) {
  const dialog = useRef(null);
  const last = run?.events.at(-1);
  return (
    <section className="panel village-panel" aria-labelledby="village-title">
      <div className="section-heading">
        <div>
          <h2 id="village-title">Smallville Live Environment</h2>
          <p className="village-subtitle">
            살아 움직이는 소문 연구실 · 마을 컨셉 뷰
          </p>
        </div>
        <span className={`village-state ${busy ? "receiving" : ""}`}>
          {busy ? "● 실행 중" : run ? "저장 기록" : "실행 대기"}
        </span>
      </div>
      <div className="village-stage">
        <VillageArtwork />
      </div>
      <div className="village-agents" aria-label="현재 실험 에이전트">
        {agents.map((agent, i) => (
          <span
            key={agent.agent_id}
            className={
              last &&
              [last.speaker_id, last.listener_id].includes(agent.agent_id)
                ? "speaking"
                : ""
            }
          >
            <i className={`avatar color-${i % 4}`}>{agent.name[0]}</i>
            {agent.name}
            <small>{agent.current_location}</small>
          </span>
        ))}
      </div>
      <div className="village-current" aria-live="polite">
        <span>
          {last
            ? `STEP ${last.step} · ${names[last.speaker_id]} → ${names[last.listener_id]}`
            : "첫 이야기를 기다리고 있습니다"}
        </span>
        <p>
          {last?.utterance ||
            "시뮬레이션을 실행하면 실제 발화와 전달 관계가 이곳에 표시됩니다."}
        </p>
      </div>
      <div className="village-footer">
        <span>배경 속 인물·말풍선은 컨셉 예시입니다.</span>
        <button
          type="button"
          className="village-expand"
          onClick={() => dialog.current.showModal()}
        >
          마을 공간 확대 ↗
        </button>
      </div>
      <dialog
        ref={dialog}
        className="village-dialog"
        aria-label="Smallville 마을 확대 보기"
        onClick={(event) => {
          if (event.target === dialog.current) dialog.current.close();
        }}
      >
        <div className="section-heading">
          <h2>Smallville · 마을 컨셉</h2>
          <button
            type="button"
            className="village-expand"
            onClick={() => dialog.current.close()}
          >
            닫기 ×
          </button>
        </div>
        <VillageArtwork />
        <p className="help">
          배경 속 인물·말풍선은 디자인 예시이며 실제 기록은 메신저와 관계망에서
          확인할 수 있습니다.
        </p>
      </dialog>
    </section>
  );
}
