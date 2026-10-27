import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import VillageScene from "./VillageScene.jsx";
import RealDataLab from "./RealDataLab.jsx";
import { LinkedResults } from "./Comparison.jsx";
import { dataHeaders } from "./dataApi.js";
import {
  StatusBar,
  ErrorBanner,
  ControlPanel,
  ConversationFeed,
} from "./components/Lab.jsx";

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...dataHeaders(),
      ...options.headers,
    },
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

function SimulationLab() {
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
  const [sourceSeed, setSourceSeed] = useState(null);
  const [mode, setMode] = useState("topic"),
    [slow, setSlow] = useState(false),
    [readOnly, setReadOnly] = useState(false),
    [cooldown, setCooldown] = useState(0);
  const abort = useRef(null),
    retryAction = useRef(null),
    latestStart = useRef(null);
  const inFlight = useRef(false),
    requestVersion = useRef(0);
  useEffect(() => {
    setSlow(false);
    if (!loading && !busy) return;
    const timer = setTimeout(() => setSlow(true), 4000);
    return () => clearTimeout(timer);
  }, [loading, busy]);
  useEffect(() => {
    if (!cooldown) return;
    const timer = setTimeout(
      () => setCooldown((value) => Math.max(0, value - 1)),
      1000,
    );
    return () => clearTimeout(timer);
  }, [cooldown]);
  useEffect(() => () => abort.current?.abort(), []);

  async function load() {
    retryAction.current = load;
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
      setReadOnly(capabilities.read_only || false);
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
    event?.preventDefault();
    retryAction.current = () => latestStart.current?.();
    if (inFlight.current) return;
    inFlight.current = true;
    requestVersion.current += 1;
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/runs/stream", {
        signal: controller.signal,
        method: "POST",
        headers: { "Content-Type": "application/json", ...dataHeaders() },
        body: JSON.stringify({
          topic,
          mode,
          steps: Number(steps),
          engine,
          ...(sourceSeed
            ? {
                dataset_id: sourceSeed.dataset_id,
                dataset_row_id: sourceSeed.dataset_row_id,
              }
            : {}),
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(
          typeof data.detail === "string"
            ? data.detail
            : "실행 요청에 실패했습니다.",
        );
        error.waitSeconds = Number(response.headers.get("Retry-After")) || 0;
        throw error;
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
            if (kind === "error") {
              const error = new Error(data.detail);
              error.waitSeconds = Number(data.retry_after) || 0;
              throw error;
            }
            if (kind === "start") setRun({ ...data, pending: true });
            if (kind === "step")
              setRun((previous) => ({
                ...previous,
                events: [...previous.events, data.event],
                completed_steps: data.event.step,
                network: data.network,
              }));
            if (kind === "analysis")
              setRun((previous) => ({
                ...previous,
                events: previous.events.map((event) =>
                  event.step === data.step
                    ? { ...event, analysis: data.analysis }
                    : event,
                ),
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
      if (err.name === "AbortError")
        setNotice(
          "중단을 요청했습니다. 이미 진행 중인 AI 호출은 과금될 수 있으며, 완료 여부는 실행 기록에서 확인할 수 있습니다.",
        );
      else {
        setError(err.message);
        setCooldown(err.waitSeconds || 0);
      }
    } finally {
      abort.current = null;
      setBusy(false);
      inFlight.current = false;
    }
  }

  latestStart.current = start;

  async function selectRun(id) {
    retryAction.current = () => selectRun(id);
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

  function seedVillage(source) {
    if (busy) return;
    setSourceSeed(source);
    setTopic(source.text);
    setMode("topic");
    setNotice(
      "실제 데이터가 연결됐습니다. 시뮬레이션 실행을 누르면 선택한 문장에서 시작하고 결과를 비공개로 저장합니다.",
    );
    nav("dashboard");
  }
  function clearSource() {
    setSourceSeed(null);
    setTopic("이번 주말 Hobbs Cafe에서 마을 파티가 열린대요.");
  }

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
          <p className="nav-label">REAL DATA</p>
          <button
            className={view === "real-data" ? "nav active" : "nav"}
            onClick={() => nav("real-data")}
          >
            <span>▤</span>실제 데이터 비교
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
          <div hidden={view === "real-data"}>
            <div className="page-heading">
              <div>
                <div className="eyebrow">ECHOCHAMBER / LIVE WORKSPACE</div>
                <h1>EchoChamber : 살아 움직이는 소문 연구실</h1>
                <p>한 사람의 이야기가 마을 전체로 퍼지는 과정을 관찰하세요.</p>
              </div>
              <span className="mode-tag">가상 마을 시뮬레이션</span>
            </div>
            <ErrorBanner
              error={error}
              onRetry={() => retryAction.current?.()}
              disabled={busy || loading}
              cooldown={cooldown}
            />
            <StatusBar
              busy={busy}
              loading={loading}
              slow={slow}
              notice={notice}
              error={error}
              readOnly={readOnly}
            />
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
                {sourceSeed && (
                  <section className="source-seed panel">
                    <div>
                      <strong>실제 데이터 연결 · {sourceSeed.title}</strong>
                      <p>
                        선택한 익명화 문장에서 시작합니다. 원문·분석과 연결
                        실험은 이 브라우저의 접근 키로만 조회합니다.
                      </p>
                    </div>
                    <button type="button" disabled={busy} onClick={clearSource}>
                      연결 해제 · 기본 주제로
                    </button>
                  </section>
                )}
                <ControlPanel
                  topicLocked={Boolean(sourceSeed)}
                  mode={mode}
                  setMode={setMode}
                  topic={topic}
                  setTopic={setTopic}
                  steps={steps}
                  setSteps={setSteps}
                  engine={engine}
                  setEngine={setEngine}
                  engines={engines}
                  busy={busy}
                  agents={agents}
                  onStart={start}
                  onStop={() => abort.current?.abort()}
                />
                <div className="workspace-grid">
                  <VillageScene
                    agents={displayAgents}
                    run={run}
                    busy={busy}
                    names={names}
                  />
                  <ConversationFeed run={run} busy={busy} names={names} />
                </div>
                <section className="panel network-panel restored-network">
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
                <LinkedResults run={run} active={view !== "real-data"} />
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
                                {item.engine === "rules"
                                  ? "규칙 기반"
                                  : "OpenAI"}
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
                    <p className="empty-history">
                      저장된 실행 기록이 없습니다.
                    </p>
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
          </div>
          <div hidden={view !== "real-data"}>
            <RealDataLab
              active={view === "real-data"}
              runs={history}
              engines={engines}
              onVillage={seedVillage}
              villageBusy={busy}
              onDeleted={(id) => {
                if (run?.source_data?.dataset_id === id) setRun(null);
                if (sourceSeed?.dataset_id === id) clearSource();
                load();
              }}
            />
          </div>
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

createRoot(document.getElementById("root")).render(<SimulationLab />);
