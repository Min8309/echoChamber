import React, { useEffect, useRef } from "react";

export function StatusBar({ busy, loading, slow, notice, error, readOnly }) {
  return (
    <div className="lab-status" role="status" aria-live="polite">
      <span className={`live-dot ${busy ? "is-busy" : ""}`} />
      {loading
        ? "서버에 연결하는 중입니다…"
        : busy
          ? "대화를 수신하고 있습니다. 완료된 실행만 저장됩니다."
          : error
            ? "연결 또는 실행에 실패했습니다."
            : notice || "실험 준비 완료"}
      {readOnly && (
        <span className="badge">에이전트·기억·메시지 읽기 전용</span>
      )}
      {slow && (
        <p>
          첫 접속에는 무료 서버가 깨어나는 시간이 걸릴 수 있습니다. 잠시 기다려
          주세요.
        </p>
      )}
    </div>
  );
}

export function ErrorBanner({ error, onRetry, disabled, cooldown }) {
  if (!error) return null;
  return (
    <div className="alert error" role="alert">
      <span>{error}</span>
      <button
        type="button"
        disabled={disabled || cooldown > 0}
        onClick={onRetry}
      >
        {cooldown > 0 ? `${cooldown}초 후 다시 시도` : "다시 시도"}
      </button>
    </div>
  );
}

export function ControlPanel({
  topicLocked = false,
  mode,
  setMode,
  topic,
  setTopic,
  steps,
  setSteps,
  engine,
  setEngine,
  engines,
  busy,
  agents,
  onStart,
  onStop,
}) {
  return (
    <form className="panel controls" onSubmit={onStart} aria-busy={busy}>
      <div className="section-heading">
        <h2>시뮬레이션 설정</h2>
        <span className="caption">
          {mode === "autonomous"
            ? "선택된 에이전트의 목표에서 대화를 시작합니다"
            : "주제를 입력하고 전파를 시작하세요"}
        </span>
      </div>
      <div className="control-row">
        <label>
          대화 방식
          <select
            aria-label="대화 방식"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            disabled={busy || topicLocked}
          >
            <option value="topic">주제 모드</option>
            <option value="autonomous">자율 모드</option>
          </select>
        </label>
        <label className="topic-field" htmlFor="topic">
          소문의 시작점
          <input
            id="topic"
            value={
              mode === "autonomous"
                ? "에이전트의 현재 목표를 사용합니다"
                : topic
            }
            onChange={(e) => setTopic(e.target.value)}
            required={mode === "topic"}
            maxLength={1000}
            placeholder="마을에 퍼뜨릴 이야기를 입력하세요"
            disabled={busy || mode === "autonomous" || topicLocked}
          />
        </label>
        <label>
          전달 단계
          <input
            aria-label="전달 단계"
            type="number"
            min="1"
            max="20"
            value={steps}
            onChange={(e) => setSteps(e.target.value)}
            required
            disabled={busy}
          />
        </label>
        <label>
          실행 모드
          <select
            aria-label="실행 모드"
            value={engine}
            onChange={(e) => setEngine(e.target.value)}
            disabled={busy}
          >
            <option value="rules">규칙 기반</option>
            {engines.includes("openai") && (
              <option value="openai">OpenAI</option>
            )}
          </select>
        </label>
        <button
          className="primary"
          type="submit"
          disabled={
            busy || agents.length < 2 || (mode === "topic" && !topic.trim())
          }
        >
          {busy ? "전파·저장 중…" : "▷ 시뮬레이션 실행"}
        </button>
        {busy && (
          <button className="stop-button" type="button" onClick={onStop}>
            중단
          </button>
        )}
      </div>
      <p className="help">
        {engine === "rules"
          ? "규칙 기반 모드: 서버에서 성향과 이전 발화로 전파를 계산합니다. AI 생성·의미 분석 결과가 아닙니다."
          : "OpenAI 모드: 단계마다 대화 생성과 분석에 각각 1회, 총 2회 호출합니다. API 비용과 서버 한도가 적용됩니다."}{" "}
        신뢰도·변화율은 실험용 지표이며 사실 여부를 판정하지 않습니다.
      </p>
      {agents.length < 2 && (
        <p className="help warning">
          저장된 에이전트가 2명 이상이어야 실행할 수 있습니다.
        </p>
      )}
    </form>
  );
}

export function MessageBubble({ event, names, waiting, engine }) {
  const analysis = event.analysis;
  const certainty = {
    confirmed: "확인된 진술",
    hearsay: "전언",
    speculation: "추측",
  };
  return (
    <li>
      <div className="feed-step">{event.step}</div>
      <div className="bubble-body">
        <div className="feed-meta">
          <strong>{names[event.speaker_id]}</strong>
          <span>→ {names[event.listener_id]}</span>
        </div>
        <p>{event.utterance}</p>
        <small>전달 신뢰도 {(event.confidence * 100).toFixed(1)}%</small>
        {analysis ? (
          <div className="analysis-tags" aria-label={`${event.step}단계 분석`}>
            <span>{analysis.is_gossip ? "가십" : "일반 대화"}</span>
            <span>{certainty[analysis.certainty] || analysis.certainty}</span>
            <span>
              평판 영향 {analysis.reputation_impact > 0 ? "+" : ""}
              {Number(analysis.reputation_impact).toFixed(2)}
            </span>
          </div>
        ) : (
          <small className="analysis-pending">
            {waiting
              ? "분석 중…"
              : engine === "rules"
                ? "규칙 기반 · AI 의미 분석 없음"
                : "분석 기록 없음"}
          </small>
        )}
      </div>
    </li>
  );
}

export function ConversationFeed({ run, busy, names }) {
  const list = useRef(null),
    follow = useRef(true);
  useEffect(() => {
    follow.current = true;
  }, [run?.run_id]);
  useEffect(() => {
    if (list.current && follow.current)
      list.current.scrollTop = list.current.scrollHeight;
  }, [run?.run_id, run?.events]);
  return (
    <section className="panel conversation-panel">
      <div className="section-heading">
        <h2>마을 메신저</h2>
        <span className="caption">
          {busy
            ? "대화 수신 중…"
            : run?.pending
              ? "미저장 기록"
              : run
                ? run.engine === "rules"
                  ? "규칙 기반 기록"
                  : "AI 생성 기록"
                : "실행 대기"}
        </span>
      </div>
      {run ? (
        <>
          <div className="source-topic">
            <small>
              {run.mode === "autonomous"
                ? "에이전트 목표에서 시작한 자율 대화"
                : "최초 이야기"}
            </small>
            <p>{run.topic}</p>
          </div>
          <ol
            className="feed"
            role="log"
            aria-label="마을 대화 기록"
            aria-live="polite"
            aria-relevant="additions text"
            ref={list}
            onScroll={() => {
              const el = list.current;
              follow.current =
                el.scrollHeight - el.scrollTop - el.clientHeight < 48;
            }}
          >
            {run.events.map((event) => (
              <MessageBubble
                key={event.step}
                event={event}
                names={names}
                engine={run.engine}
                waiting={busy && run.pending && event.analysis === undefined}
              />
            ))}
          </ol>
        </>
      ) : (
        <div className="empty">
          <span>◇</span>
          <h3>아직 전달된 이야기가 없습니다</h3>
          <p>
            위에서 시뮬레이션을 실행하면
            <br />
            실제 전달 기록이 여기에 표시됩니다.
          </p>
        </div>
      )}
    </section>
  );
}
