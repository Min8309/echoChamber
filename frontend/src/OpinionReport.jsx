import React, { useEffect, useRef, useState } from "react";
import { researchApi } from "./dataApi.js";
import ReportVisuals from "./ReportVisuals.jsx";

export default function OpinionReport({ dataset, hasAI, autoGenerate = false }) {
  const [source, setSource] = useState("");
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const version = useRef(0);
  const sample = report?.sections.find(s => s.number === 10)?.result;
  const total = sample?.["전체 댓글"] ?? dataset.rows.length;
  const analysed = sample?.["AI 분석 완료"] ?? 0;
  useEffect(() => {
    version.current++;
    setReport(null);
    setError("");
    setBusy(false);
  }, [dataset, source]);
  useEffect(() => {
    if (autoGenerate) generate(false);
    return () => { version.current++; };
  }, [dataset, autoGenerate]);
  async function generate(useAI) {
    const current = ++version.current;
    setBusy(true);
    setError("");
    try {
      const result = await researchApi(`/datasets/${dataset.dataset_id}/opinion-report`, {
        method: "POST", body: JSON.stringify({ source_text: source, use_ai: useAI }),
      });
      if (current === version.current) setReport(result);
    } catch (err) {
      if (current === version.current) setError(err.message);
    } finally {
      if (current === version.current) setBusy(false);
    }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "comment-opinion-report.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <section className="panel opinion-report" aria-label="댓글 여론 변형 리포트">
    <h2>댓글 여론 변형 리포트</h2>
    <p>표본의 주장·표현·감정·답글 관계를 한눈에 확인하세요. 근거 댓글은 필요한 항목에서 펼쳐 볼 수 있습니다.</p>
    <label>비교할 원문 (선택 · 최대 12,000자)
      <textarea value={source} maxLength={12000} rows={4} onChange={e => setSource(e.target.value)} placeholder="기사·영상 대본 등의 원문을 입력하세요. 개인정보와 이용 권한을 확인해 주세요." />
    </label>
    <p className="research-help">원문은 이 리포트 요청에만 사용하며 저장하지 않습니다. AI 원문 비교를 실행하면 원문과 댓글이 AI 서비스로 전송됩니다. 다운로드 파일에는 원문이 포함됩니다.</p>
    <div className="button-row">
      <button type="button" disabled={busy} onClick={() => generate(false)}>10개 항목 리포트 생성</button>
      <button type="button" disabled={busy || !hasAI || !source.trim()} onClick={() => generate(true)}>AI 원문 비교 포함 · 1회 호출</button>
      {report && <button type="button" onClick={download}>10개 항목 JSON 다운로드</button>}
    </div>
    {busy && <p role="status">리포트 분석 중…</p>}
    {error && <p role="alert">{error}</p>}
    {report && <div aria-live="polite">
      <div className="report-overview" aria-label="분석 요약">
        {[["전체 댓글", `${total}건`], ["AI 분석 완료", `${analysed} / ${total}건`], ["미분석", `${total - analysed}건`], ["원문 비교", sample?.["원문 비교"] || "미실행"]].map(([label, value]) => <div className="report-overview-card" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
      <div className="report-coverage"><div className="report-bar-label"><strong>댓글 AI 분석 진행률</strong><span>{total ? Math.round(analysed / total * 100) : 0}%</span></div><progress value={analysed} max={Math.max(total, 1)} aria-label="댓글 AI 분석 진행률" /></div>
      {analysed < total && <p className="report-callout">{total - analysed}건이 AI 미분석 상태입니다. 주장·감정 결과는 분석 완료 {analysed}건만 기준으로 합니다. 아래 ‘AI 분석 / 이어서 분석’에서 분석할 수 있습니다.</p>}
      <nav className="report-index" aria-label="리포트 항목 바로가기">{report.sections.map(s => <a key={s.number} href={`#report-section-${s.number}`}>{s.number}. {s.title}</a>)}</nav>
      <div className="report-sections">{report.sections.map(section => <article id={`report-section-${section.number}`} className={`report-section report-section-${section.number}`} key={section.number}>
        <h3><span>{String(section.number).padStart(2, "0")}</span>{section.title}</h3>
        <ReportVisuals section={section} dataset={dataset} analysed={analysed} />
        <details className="report-method"><summary>해석 기준·한계</summary><p>{section.number === 4 ? "전체 댓글 중 과장·단정·추측에 해당하는 표현을 포함한 댓글 비율입니다. 범주는 중복될 수 있으며 문맥과 부정문을 판별하지 않는 문자열 규칙입니다." : section.note}</p></details>
      </article>)}</div>
    </div>}
  </section>;
}
