import React from "react";

export default function DiscussionResults({ run }) {
  if (!run?.source_data?.discussion) return null;
  const events = run.events || [],
    rows = run.source_data.rows || [];
  const mentioned = new Set(
    events.flatMap((event) => event.source_row_ids || []),
  );
  const analysed = events.filter((event) => event.analysis);
  const counts = Object.fromEntries(
    run.agents.map((agent) => [
      agent.agent_id,
      events.filter((event) => event.speaker_id === agent.agent_id).length,
    ]),
  );
  const colors = ["#3366cc", "#0d9488", "#ae6c26", "#8b5bc4"];
  const points = (key) =>
    events
      .map(
        (event, index) =>
          `${42 + (index * 590) / Math.max(1, events.length - 1)},${142 - Math.max(0, Math.min(1, event[key])) * 120}`,
      )
      .join(" ");
  return (
    <section className="panel discussion-results" aria-label="자료 토론 시각화">
      <div className="section-heading">
        <h2>자료 토론 · 대화 흐름 분석</h2>
        <span className="caption">
          {run.engine === "openai"
            ? "AI 대화 · 발화별 의미 분석"
            : "규칙 템플릿 · AI 의미 분석 없음"}
        </span>
      </div>
      <div className="discussion-stat-grid">
        <article>
          <span>참여 인물</span>
          <strong>{run.agents.length}명</strong>
        </article>
        <article>
          <span>검토 자료 배정</span>
          <strong>
            {mentioned.size}/{rows.length}건
          </strong>
        </article>
        <article>
          <span>대화 단계</span>
          <strong>{events.length}회</strong>
        </article>
        <article>
          <span>AI 의미 분석 완료</span>
          <strong>
            {analysed.length}/{events.length}회
          </strong>
        </article>
      </div>
      <div className="discussion-charts">
        <article>
          <h3>인물별 발언 횟수</h3>
          {run.agents.map((agent, index) => (
            <div className="discussion-bar" key={agent.agent_id}>
              <span>{agent.name}</span>
              <div>
                <i
                  style={{
                    width: `${(100 * counts[agent.agent_id]) / Math.max(1, events.length)}%`,
                    background: colors[index % 4],
                  }}
                />
              </div>
              <strong>{counts[agent.agent_id]}회</strong>
            </div>
          ))}
        </article>
        <article>
          <h3>발화의 AI 감정 분류</h3>
          {[
            ["positive", "긍정"],
            ["neutral", "중립"],
            ["negative", "부정"],
          ].map(([key, label], index) => {
            const count = analysed.filter(
              (event) => event.analysis.sentiment === key,
            ).length;
            return (
              <div className="discussion-bar" key={key}>
                <span>{label}</span>
                <div>
                  <i
                    style={{
                      width: `${(100 * count) / Math.max(1, analysed.length)}%`,
                      background: colors[index],
                    }}
                  />
                </div>
                <strong>{analysed.length ? `${count}회` : "—"}</strong>
              </div>
            );
          })}
          <small>AI 분석이 도착한 발화만 집계합니다.</small>
        </article>
        <article className="discussion-trend">
          <h3>단계별 전달 지표</h3>
          <svg
            viewBox="0 0 660 180"
            role="img"
            aria-label="단계별 전달 신뢰도와 첫 자료 대비 문자열 변화율"
          >
            <path d="M42 22V142H632" fill="none" stroke="#cbd5e1" />
            <text x="0" y="28">
              100%
            </text>
            <text x="12" y="146">
              0%
            </text>
            <polyline
              points={points("confidence")}
              fill="none"
              stroke="#3366cc"
              strokeWidth="3"
            />
            <polyline
              points={points("distortion")}
              fill="none"
              stroke="#0d9488"
              strokeWidth="3"
            />
            <text x="42" y="170">
              1단계
            </text>
            <text x="585" y="170">
              {events.length}단계
            </text>
          </svg>
          <p>파랑: 성향 기반 전달 신뢰도 · 초록: 첫 자료 대비 문자열 변화율</p>
          <small>
            문자열 차이는 자료 간 주제 차이도 반영합니다. 사실성·정보 정확도
            점수가 아닙니다.
          </small>
        </article>
      </div>
      <details className="discussion-timeline">
        <summary>자료별 검토 순서 · 대화 기록 보기</summary>
        <ol>
          {events.map((event) => (
            <li key={event.step}>
              <strong>
                {event.step}단계 ·{" "}
                {
                  run.agents.find(
                    (agent) => agent.agent_id === event.speaker_id,
                  )?.name
                }{" "}
                · {event.discussion_stage}
              </strong>
              <span>이번 참고 자료 {event.source_number}번</span>
              <p>{event.utterance}</p>
            </li>
          ))}
        </ol>
        <small>
          자료 배정은 실험 순서이며, 모델이 근거를 정확히 인용했는지 자동 검증한
          결과는 아닙니다.
        </small>
      </details>
    </section>
  );
}
