import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "요청에 실패했습니다. 서버 연결과 입력값을 확인해 주세요.",
    );
  return data;
}

function Network({ network }) {
  const nodes = network?.nodes || [];
  const points = Object.fromEntries(
    nodes.map((node, i) => {
      const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
      return [
        node.id,
        { x: 260 + 165 * Math.cos(angle), y: 200 + 130 * Math.sin(angle) },
      ];
    }),
  );
  return (
    <svg
      className="network"
      viewBox="0 0 520 400"
      role="img"
      aria-label={`소문 확산 네트워크: 에이전트 ${nodes.length}명, 전달 경로 ${network?.edges?.length || 0}개`}
    >
      <defs>
        <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="#cbd5e1" />
        </pattern>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="10"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#3366cc" />
        </marker>
      </defs>
      <rect width="520" height="400" fill="url(#grid)" />
      {(network?.edges || []).map((edge) => {
        const a = points[edge.source],
          b = points[edge.target];
        if (!a || !b) return null;
        const dx = b.x - a.x,
          dy = b.y - a.y,
          len = Math.hypot(dx, dy);
        const x1 = a.x + (dx * 31) / len,
          y1 = a.y + (dy * 31) / len;
        const x2 = b.x - (dx * 36) / len,
          y2 = b.y - (dy * 36) / len;
        // Offset directed paths so A → B and B → A remain distinguishable.
        const mx = (x1 + x2) / 2 - dy * 0.12,
          my = (y1 + y2) / 2 + dx * 0.12;
        return (
          <g key={`${edge.source}-${edge.target}`}>
            <path
              d={`M${x1},${y1} Q${mx},${my} ${x2},${y2}`}
              fill="none"
              stroke="#3366cc"
              strokeOpacity=".65"
              strokeWidth={Math.min(5, 1.5 + edge.count)}
              markerEnd="url(#arrow)"
            />
            <text x={mx} y={my - 6} className="edge-label">
              {edge.count}회
            </text>
          </g>
        );
      })}
      {nodes.map((node, i) => (
        <g
          key={node.id}
          transform={`translate(${points[node.id].x},${points[node.id].y})`}
        >
          <circle
            r="29"
            fill={["#e7ebff", "#ccfbf1", "#fef3c7", "#f3e8ff"][i % 4]}
            stroke="white"
            strokeWidth="4"
          />
          <text
            textAnchor="middle"
            dy="6"
            fontSize="18"
            fill="#204fa6"
            fontWeight="700"
          >
            {node.name[0]}
          </text>
          <text textAnchor="middle" y="49" className="node-name">
            {node.name} · {i + 1}
          </text>
          <text textAnchor="middle" y="65" className="node-job">
            {node.occupation}
          </text>
        </g>
      ))}
    </svg>
  );
}

function App() {
  const [agents, setAgents] = useState([]),
    [history, setHistory] = useState([]);
  const [run, setRun] = useState(null),
    [engines, setEngines] = useState(["rules"]);
  const [topic, setTopic] = useState(
    "이번 주말 Hobbs Cafe에서 마을 파티가 열린대요.",
  );
  const [steps, setSteps] = useState(6),
    [engine, setEngine] = useState("rules");
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [notice, setNotice] = useState(""),
    [view, setView] = useState("dashboard");
  const inFlight = useRef(false),
    requestVersion = useRef(0);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [roster, saved, capabilities] = await Promise.all([
        api("/agents"),
        api("/runs"),
        api("/capabilities"),
      ]);
      setAgents(roster);
      setHistory(saved);
      setEngines(capabilities.engines);
      setRun(saved.length ? await api(`/runs/${saved[0].run_id}`) : null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function start(event) {
    event.preventDefault();
    if (inFlight.current) return;
    inFlight.current = true;
    requestVersion.current += 1;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/runs/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, steps: Number(steps), engine }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "실행 요청에 실패했습니다.",
        );
      }
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "",
        saved = null;
      try {
        while (true) {
          const { done, value } = await reader.read();
          buffer += decoder.decode(value, { stream: !done });
          let boundary;
          while ((boundary = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const kind = frame.match(/^event: (.+)$/m)?.[1];
            const payload = frame.match(/^data: (.+)$/m)?.[1];
            if (!payload) continue;
            const data = JSON.parse(payload);
            if (kind === "error") throw new Error(data.detail);
            if (kind === "start") setRun({ ...data, pending: true });
            if (kind === "step")
              setRun((previous) => ({
                ...previous,
                events: [...previous.events, data.event],
                completed_steps: data.event.step,
                network: data.network,
              }));
            if (kind === "complete") saved = data;
          }
          if (done) break;
        }
      } finally {
        await reader.cancel().catch(() => {});
      }
      if (!saved)
        throw new Error(
          "연결이 끊겼습니다. 실행 기록을 다시 불러와 저장 여부를 확인해 주세요.",
        );
      setRun(saved);
      setView("dashboard");
      setNotice(
        "실행 결과가 저장되었습니다. 새로고침 후에도 조회할 수 있습니다.",
      );
      setHistory((previous) =>
        [
          {
            run_id: saved.run_id,
            created_at: saved.created_at,
            topic: saved.topic,
            engine: saved.engine,
            completed_steps: saved.completed_steps,
          },
          ...previous,
        ].slice(0, 100),
      );
    } catch (err) {
      setRun((previous) =>
        previous?.pending ? { ...previous, interrupted: true } : previous,
      );
      setError(err.message);
    } finally {
      setBusy(false);
      inFlight.current = false;
    }
  }

  async function selectRun(id) {
    const version = ++requestVersion.current;
    setError("");
    setNotice("");
    try {
      const saved = await api(`/runs/${id}`);
      if (version === requestVersion.current) setRun(saved);
    } catch (err) {
      if (version === requestVersion.current) setError(err.message);
    }
  }
  const displayAgents = run?.agents || agents;
  const network = run?.network || {
    nodes: agents.map((a) => ({
      id: a.agent_id,
      name: a.name,
      occupation: a.occupation,
    })),
    edges: [],
  };
  const names = Object.fromEntries(
    displayAgents.map((a, i) => [a.agent_id, `${a.name} · ${i + 1}`]),
  );
  const last = run?.events.at(-1);
  const nav = (next) => {
    setView(next);
    document
      .getElementById(
        next === "agents"
          ? "agents"
          : next === "history"
            ? "history"
            : "workspace",
      )
      ?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="EchoChamber 홈">
          <span className="brand-icon">E</span>
          <span>
            EchoChamber<small>RUMOR DYNAMICS LAB</small>
          </span>
        </a>
        <div className="project">
          <span className="project-symbol">◎</span>
          <div>
            Smallville 프로젝트<small>가상 마을 · 소문 전파 실험</small>
          </div>
          <span className="live-dot" />
        </div>
        <nav aria-label="메인 메뉴">
          <p className="nav-label">OVERVIEW</p>
          <button
            className={view === "dashboard" ? "nav active" : "nav"}
            onClick={() => nav("dashboard")}
          >
            <span>▦</span>대시보드
          </button>
          <p className="nav-label">SIMULATION</p>
          <button
            className={view === "agents" ? "nav active" : "nav"}
            onClick={() => nav("agents")}
          >
            <span>♙</span>마을 에이전트
          </button>
          <button
            className="nav"
            onClick={() => {
              nav("dashboard");
              document.getElementById("topic").focus();
            }}
          >
            <span>▷</span>시뮬레이션 실행
          </button>
          <p className="nav-label">ARCHIVE</p>
          <button
            className={view === "history" ? "nav active" : "nav"}
            onClick={() => nav("history")}
          >
            <span>◷</span>실행 기록
          </button>
        </nav>
        <div className="sidebar-foot">
          <span className="live-dot" /> EchoChamber Workbench
          <small>React + FastAPI</small>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span className="muted">워크스페이스</span>
            <span className="slash">/</span>
            <strong>소문 역학 연구실</strong>
          </div>
          <span className="badge">SMALLVILLE</span>
        </header>
        <main id="workspace">
          <div className="page-heading">
            <div>
              <div className="eyebrow">ECHOCHAMBER / LIVE WORKSPACE</div>
              <h1>소문이 흐르는 마을</h1>
              <p>한 사람의 이야기가 마을 전체로 퍼지는 과정을 관찰하세요.</p>
            </div>
            <span className="mode-tag">가상 마을 시뮬레이션</span>
          </div>
          {error && (
            <div className="alert error" role="alert">
              {error}{" "}
              <button disabled={busy} onClick={load}>
                다시 연결
              </button>
            </div>
          )}
          {busy && (
            <div className="alert success" role="status">
              대화가 도착할 때마다 관계망을 갱신합니다. 완료된 실행만 히스토리에
              저장됩니다.
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              {notice}
            </div>
          )}
          {loading ? (
            <div className="panel loading" role="status">
              에이전트와 실행 기록을 불러오는 중입니다…
            </div>
          ) : (
            <>
              <section className="metrics" aria-label="실행 통계">
                <Metric
                  label="마을 에이전트"
                  value={displayAgents.length}
                  unit="명"
                  note="서버에 저장된 에이전트"
                />
                <Metric
                  label="전달 횟수"
                  value={run?.completed_steps || 0}
                  unit="회"
                  note="선택한 실행의 대화 단계"
                />
                <Metric
                  label="전달 신뢰도"
                  value={last ? (last.confidence * 100).toFixed(1) : "—"}
                  unit={last ? "%" : ""}
                  note="성향 기반 감쇠 지표"
                />
                <Metric
                  label="문자열 변화율"
                  value={last ? (last.distortion * 100).toFixed(1) : "—"}
                  unit={last ? "%" : ""}
                  note="원문 대비 마지막 발화 차이"
                />
              </section>
              <form className="panel controls" onSubmit={start}>
                <div className="section-heading">
                  <h2>시뮬레이션 설정</h2>
                  <span className="caption">
                    주제를 입력하고 전파를 시작하세요
                  </span>
                </div>
                <div className="control-row">
                  <label className="topic-field" htmlFor="topic">
                    소문의 시작점
                    <input
                      id="topic"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      required
                      maxLength={1000}
                      placeholder="마을에 퍼뜨릴 이야기를 입력하세요"
                      disabled={busy}
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
                    disabled={busy || agents.length < 2 || !topic.trim()}
                  >
                    {busy ? "전파·저장 중…" : "▷ 시뮬레이션 실행"}
                  </button>
                </div>
                <p className="help">
                  {engine === "rules"
                    ? "규칙 기반 모드: 에이전트 성향과 이전 발화를 사용해 서버에서 전파를 계산합니다. AI 생성 결과가 아닙니다."
                    : "OpenAI 모드: 각 전달 발화를 AI로 생성합니다. 실행 단계 수만큼 API 비용이 발생할 수 있습니다."}{" "}
                  신뢰도·변화율은 실험용 지표이며 사실 여부를 판정하지 않습니다.
                </p>
                {agents.length < 2 && (
                  <p className="help warning">
                    저장된 에이전트가 2명 이상이어야 실행할 수 있습니다.
                  </p>
                )}
              </form>
              <div className="workspace-grid">
                <section className="panel network-panel">
                  <div className="section-heading">
                    <h2>소문 확산 네트워크</h2>
                    <span className="badge">
                      {run ? `${run.completed_steps} STEPS` : "READY"}
                    </span>
                  </div>
                  <Network network={network} />
                  <div className="legend">
                    <span className="live-dot" /> 에이전트{" "}
                    <span className="line-key" /> 전달 방향 · 선 위 숫자는 전달
                    횟수
                  </div>
                </section>
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
                        <small>최초 이야기</small>
                        <p>{run.topic}</p>
                      </div>
                      <ol className="feed">
                        {run.events.map((e) => (
                          <li key={e.step}>
                            <div className="feed-step">{e.step}</div>
                            <div>
                              <div className="feed-meta">
                                <strong>{names[e.speaker_id]}</strong>
                                <span>→ {names[e.listener_id]}</span>
                              </div>
                              <p>{e.utterance}</p>
                              <small>
                                전달 신뢰도 {(e.confidence * 100).toFixed(1)}% ·{" "}
                                {e.certainty === "hearsay" ? "전언" : "추측"}
                              </small>
                            </div>
                          </li>
                        ))}
                      </ol>
                    </>
                  ) : (
                    <div className="empty">
                      <span>◇</span>
                      <h3>아직 전달된 이야기가 없습니다</h3>
                      <p>
                        위에서 주제를 입력하고 시뮬레이션을 실행하면
                        <br />
                        실제 전달 기록이 여기에 표시됩니다.
                      </p>
                    </div>
                  )}
                </section>
              </div>
              <section className="panel" id="agents">
                <div className="section-heading">
                  <h2>마을 에이전트</h2>
                  <span className="caption">
                    {run
                      ? "선택한 실행 당시의 에이전트"
                      : "현재 저장된 에이전트"}{" "}
                    · {displayAgents.length}명
                  </span>
                </div>
                <div className="agent-grid">
                  {displayAgents.map((agent, i) => (
                    <article className="agent" key={agent.agent_id}>
                      <div className={`avatar color-${i % 4}`}>
                        {agent.name[0]}
                      </div>
                      <div>
                        <h3>
                          {agent.name} <small>#{i + 1}</small>
                        </h3>
                        <p>
                          {agent.occupation} · {agent.age}세
                        </p>
                        <small>{agent.current_location}</small>
                      </div>
                      <div className="traits">
                        {[
                          ["사교성", "sociability"],
                          ["전파 성향", "gossip_tendency"],
                          ["수용 성향", "credulity"],
                        ].map(([label, key]) => (
                          <div key={key}>
                            <span>{label}</span>
                            <meter
                              min="0"
                              max="1"
                              value={agent.personality[key]}
                            />
                            {Math.round(agent.personality[key] * 100)}%
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
              <section className="panel" id="history">
                <div className="section-heading">
                  <h2>실행 아카이브</h2>
                  <span className="caption">
                    최근 100개 · 저장된 기록을 다시 열어보세요
                  </span>
                </div>
                {history.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>실행 시간</th>
                          <th>시작 이야기</th>
                          <th>모드</th>
                          <th>단계</th>
                          <th>결과</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.map((item) => (
                          <tr
                            key={item.run_id}
                            className={
                              run?.run_id === item.run_id ? "selected" : ""
                            }
                          >
                            <td>
                              {new Date(item.created_at).toLocaleString(
                                "ko-KR",
                                { timeZone: "Asia/Seoul" },
                              )}
                            </td>
                            <td className="history-topic">{item.topic}</td>
                            <td>
                              {item.engine === "rules" ? "규칙 기반" : "OpenAI"}
                            </td>
                            <td>{item.completed_steps}회</td>
                            <td>
                              <button
                                disabled={busy}
                                className="text-button"
                                onClick={() => selectRun(item.run_id)}
                                aria-label={`${item.topic} 결과 보기`}
                              >
                                {run?.run_id === item.run_id
                                  ? "선택됨"
                                  : "결과 보기"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="empty-history">저장된 실행 기록이 없습니다.</p>
                )}
              </section>
              {run && (
                <p className="run-id">
                  RUN ID · {run.run_id} ·{" "}
                  {run.pending
                    ? run.interrupted
                      ? "실행 중단 · 저장되지 않음"
                      : "수신 중 · 아직 저장되지 않음"
                    : "서버 저장 완료"}
                </p>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
function Metric({ label, value, unit, note }) {
  return (
    <article className="panel metric">
      <span>{label}</span>
      <div>
        {value}
        <small>{unit}</small>
      </div>
      <p>{note}</p>
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
