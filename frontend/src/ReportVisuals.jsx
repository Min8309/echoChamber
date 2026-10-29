import React from "react";

const labels = { positive: "긍정", neutral: "중립", negative: "부정", confirmed: "확정 표현", hearsay: "전언", speculation: "추측" };
const colors = { 긍정: "#0d9488", 중립: "#94a3b8", 부정: "#e16b58", 과장: "#e16b58", 단정: "#7464c4", 추측: "#d99a24" };

export function Empty({ children }) {
  return <div className="report-empty"><span aria-hidden="true">◌</span><p>{children}</p></div>;
}

export function Evidence({ rows = [], title = "근거 댓글" }) {
  return rows.length ? <details className="report-evidence"><summary>{title} {rows.length}건 보기</summary>
    {rows.map((row, i) => <blockquote key={`${row.row_id}-${i}`}><strong>댓글 {row.number}</strong><p>{row.text}</p></blockquote>)}
  </details> : null;
}

function Comment({ row }) {
  return row ? <details className="report-comment"><summary><span className="report-chip">댓글 {row.number}</span> {row.text.slice(0, 90)}{row.text.length > 90 ? "…" : ""}</summary><p>{row.text}</p></details> : "—";
}

function Table({ headers, children, label }) {
  return <div className="report-table-scroll" tabIndex={0} role="region" aria-label={label}><table className="report-table"><thead><tr>{headers.map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
}

function Bar({ label, count, denominator, percent, color }) {
  const pct = percent ?? (denominator ? Math.round(count / denominator * 1000) / 10 : null);
  return <div className="report-bar-row">
    <div className="report-bar-label"><strong>{label}</strong><span>{count} / {denominator}건 <b>{pct === null ? "미분석" : `${pct}%`}</b></span></div>
    {pct !== null && <div className="report-bar-track" role="meter" aria-label={`${label} 댓글 비율`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}><span style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color || "#3366cc" }} /></div>}
  </div>;
}

function Findings({ items, pending, empty }) {
  if (items == null) return <Empty>{pending}</Empty>;
  if (!items.length) return <Empty>{empty}</Empty>;
  return <Table label="주장과 근거 댓글" headers={["분석 내용", "근거"]}>{items.map((item, i) => <tr key={i}><td>{item["내용"]}</td><td><Evidence rows={item["근거 댓글"]} /></td></tr>)}</Table>;
}

function Sentiments({ result, analysed }) {
  const distribution = result["분포"];
  if (!analysed) return <Empty>댓글 AI 분석 0건 · 감정 분포를 아직 계산하지 않았습니다. 미분석 {result["미분석"]}건을 중립이나 0%로 표시하지 않습니다.</Empty>;
  let end = 0;
  const segments = Object.entries(distribution).map(([label, data]) => {
    const start = end;
    end += data["비율(%)"] || 0;
    return `${colors[label]} ${start}% ${end}%`;
  });
  return <div className="report-sentiments">
    <div className="report-donut" role="img" aria-label={Object.entries(distribution).map(([label, d]) => `${label} ${d["비율(%)"]}%`).join(", ")} style={{ background: `conic-gradient(${segments.join(",")})` }}><div><strong>{analysed}건</strong><span>AI 분석 표본</span></div></div>
    <div className="report-bar-list">{Object.entries(distribution).map(([label, d]) => <Bar key={label} label={label} count={d["댓글 수"]} denominator={d["분모"]} percent={d["비율(%)"]} color={colors[label]} />)}<p className="report-subtle">미분석 {result["미분석"]}건 제외</p></div>
  </div>;
}

function Replies({ pairs, dataset }) {
  if (!pairs.length) return <Empty>저장된 댓글 사이에 비교할 수 있는 답글 연결이 없습니다.</Empty>;
  const byId = Object.fromEntries(dataset.rows.map(r => [r.row_id, r]));
  return <><p className="report-subtle">실제 부모 댓글과 답글 {pairs.length}쌍 · 댓글을 누르면 전문을 볼 수 있습니다.</p>
    <Table label="부모 댓글과 답글 변화 비교" headers={["부모 댓글", "답글", "변화 지점"]}>{pairs.map((pair, i) => {
      const parent = pair["부모 댓글"], reply = pair["답글"];
      const ai = Object.entries(pair["AI 분류 변화"]);
      const expressions = Object.entries(pair["표현 변화"]);
      const complete = byId[parent.row_id]?.analysis && byId[reply.row_id]?.analysis;
      return <tr key={i}><td><Comment row={parent} /></td><td><Comment row={reply} /></td><td>
        {ai.map(([key, value]) => <p className="report-change" key={key}>{key === "sentiment" ? "감정" : "확실성"}: {labels[value["부모"]] || value["부모"]} → {labels[value["답글"]] || value["답글"]}</p>)}
        {expressions.map(([key, value]) => <p className="report-change" key={key}>{key}: {value["부모"] ? "있음" : "없음"} → {value["답글"] ? "있음" : "없음"}</p>)}
        {!complete && <span className="report-chip">AI 비교 미완료</span>}
        {!ai.length && !expressions.length && <p className="report-subtle">{complete ? "분류·표현 규칙 변화 없음" : "표현 규칙 변화 없음"}</p>}
      </td></tr>;
    })}</Table></>;
}

function Timeline({ days }) {
  if (!days.length) return <Empty>작성일이 없어 날짜별 변화를 계산할 수 없습니다.</Empty>;
  const maximum = Math.max(...days.map(d => d["댓글 수"]), 1);
  const width = Math.max(360, days.length * 66);
  const spacing = (width - 60) / days.length;
  return <>
    {days.length === 1 && <p className="report-callout">작성일이 하루에 모여 있어 시간에 따른 추세는 판단할 수 없습니다.</p>}
    <div className="report-timeline-scroll"><svg className="report-timeline" role="img" aria-label={`날짜별 표본 댓글 수: ${days.map(d => `${d["날짜"]} ${d["댓글 수"]}건`).join(", ")}`} viewBox={`0 0 ${width} 220`} style={{ minWidth: width }}>
      {[0, 0.5, 1].map(f => <g key={f}><line x1="36" x2={width - 10} y1={175 - 140 * f} y2={175 - 140 * f} stroke="#e2e8f0" /><text x="29" y={179 - 140 * f} textAnchor="end">{Math.round(maximum * f)}</text></g>)}
      {days.map((day, i) => {
        const x = 36 + spacing * (i + .5), height = day["댓글 수"] / maximum * 140;
        return <g key={day["날짜"]}><title>{day["날짜"]}: {day["댓글 수"]}건, AI 분석 {day["분석 완료"]}건</title><rect x={x - Math.min(18, spacing * .3)} y={175 - height} width={Math.min(36, spacing * .6)} height={height} fill="#3366cc" rx="4" /><text x={x} y={166 - height} textAnchor="middle">{day["댓글 수"]}건</text><text x={x} y="199" textAnchor="middle">{day["날짜"].slice(5)}</text></g>;
      })}
    </svg></div>
    <Table label="날짜별 댓글과 주장 빈도" headers={["작성일", "댓글", "AI 분석", "주장별 빈도"]}>{days.map(day => <tr key={day["날짜"]}><th scope="row">{day["날짜"]}</th><td>{day["댓글 수"]}건</td><td>{day["분석 완료"]}건</td><td>{Object.keys(day["주장별 댓글 수"]).length ? <details><summary>주장별 빈도 보기</summary><ul>{Object.entries(day["주장별 댓글 수"]).map(([claim, n]) => <li key={claim}>{claim} · {n}건</li>)}</ul></details> : "AI 미분석"}</td></tr>)}</Table>
    <p className="report-subtle">표본의 일별 빈도이며 실제 여론의 확산 속도가 아닙니다.</p>
  </>;
}

export default function ReportVisuals({ section, dataset, analysed }) {
  const r = section.result;
  switch (section.number) {
    case 1: return <><div className="report-topic"><span className="report-subtle">분석 주제</span><h4>{r["주제"]}</h4></div>{r["원문 요약"] ? <p className="report-source-summary">{r["원문 요약"]}</p> : <Empty>{r["원문"] ? "원문을 입력했습니다. AI 원문 비교를 실행하면 핵심 요약이 표시됩니다." : "비교할 기사·영상 대본을 입력하면 원문 요약을 확인할 수 있습니다."}</Empty>}{r["원문"] && <details className="report-evidence"><summary>비교 원문 전문 보기</summary><p className="report-source-text">{r["원문"]}</p></details>}</>;
    case 2: return r.length ? <Table label="주요 댓글 주장 순위" headers={["순위", "주장 · 분석 표본 내 비율", "근거"]}>{r.map((item, i) => <tr key={i}><td><span className="report-rank">{i + 1}</span></td><td><Bar label={item["주장"]} count={item["댓글 수"]} denominator={analysed} /></td><td><Evidence rows={item["근거 댓글"]} /></td></tr>)}</Table> : <Empty>{analysed ? "분석된 댓글에서 집계할 주장 문구를 찾지 못했습니다." : "댓글 AI 분석 후 주장 TOP 5가 표시됩니다. 현재는 미분석 상태입니다."}</Empty>;
    case 3: return <Findings items={r} pending="원문 비교 미실행 · 원문을 입력하고 AI 원문 비교를 실행해 주세요." empty="이번 원문 비교에서 원문이 뒷받침하지 않는 주장 후보가 발견되지 않았습니다." />;
    case 4: return <div className="report-expression-grid">{Object.entries(r).map(([label, data]) => <div className="report-expression" key={label}><span className="report-chip" style={{ color: colors[label] }}>{label}</span><strong className="report-big-number">{data["비율(%)"] ?? "—"}<small>%</small></strong><Bar label={label} count={data["댓글 수"]} denominator={data["분모"]} percent={data["비율(%)"]} color={colors[label]} /><Evidence rows={data["근거 댓글"]} /></div>)}</div>;
    case 5: return <Sentiments result={r} analysed={analysed} />;
    case 6: return <Replies pairs={r} dataset={dataset} />;
    case 7: return <Timeline days={r} />;
    case 8: return r.length ? <Table label="주의해서 해석할 댓글 후보" headers={["검토 댓글", "확인할 표현"]}>{r.map((item, i) => <tr key={i}><td><Comment row={item["댓글"]} /></td><td>{item["표현 규칙"].map(label => <span className="report-chip" key={label}>{label}</span>)}</td></tr>)}</Table> : <Empty>설정된 표현 규칙에 해당하는 검토 후보가 없습니다. 댓글의 사실성을 보증하는 결과는 아닙니다.</Empty>;
    case 9: return <div className="report-viewpoints"><div><h4>빈도 상위 주장 예시</h4>{r["빈도 상위 주장 예시"].length ? r["빈도 상위 주장 예시"].map(row => <Comment key={row.row_id} row={row} />) : <Empty>댓글 AI 분석 후 대표 예시가 표시됩니다.</Empty>}</div><div><h4>반대 관점 후보</h4><Findings items={r["반대 관점 후보"]} pending="AI 원문 비교를 실행하면 반대 관점 후보를 확인할 수 있습니다." empty="이번 분석에서 반대 관점 후보가 확인되지 않았습니다." /></div></div>;
    case 10: {
      const origin = r["출처"];
      const sourceURL = /^https?:\/\//i.test(origin?.source_url || "") ? origin.source_url : null;
      return <><Table label="분석 표본과 출처" headers={["항목", "내용"]}>
        {[["표본", `${r["전체 댓글"]}건 · AI 분석 ${r["AI 분석 완료"]}건`], ["댓글 작성일 범위", r["수집일 범위"]?.join(" ~ ") || "작성일 없음"], ["출처", origin?.name || "직접 입력·파일 가져오기"], ["원문 비교", r["원문 비교"]], ["분석 모델·버전", r["분석 모델·버전"].join(", ") || "AI 미분석"], ["이용 조건", origin?.license || "사용자가 이용 권한을 확인한 자료"]].map(([key, value]) => <tr key={key}><th scope="row">{key}</th><td>{value}</td></tr>)}
      </Table>{sourceURL && <p><a href={sourceURL} target="_blank" rel="noreferrer">자료 출처 열기 ↗</a></p>}{origin?.truncated && <p className="report-callout">수집 한도로 일부 댓글만 포함된 표본입니다.</p>}{origin?.attribution && <details className="report-evidence"><summary>출처 표시·변경 사항</summary><p>{origin.attribution}</p><p>{origin.changes}</p></details>}</>;
    }
    default: return null;
  }
}
