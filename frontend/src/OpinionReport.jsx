import React, { useEffect, useRef, useState } from "react";
import { researchApi } from "./dataApi.js";

function Result({ value }) {
  if (value === null || value === undefined) return <p>자료 부족 또는 분석 미실행</p>;
  if (Array.isArray(value)) return value.length ? <ol>{value.map((item, i) => <li key={i}><Result value={item} /></li>)}</ol> : <p>해당 결과 없음 · 분석 범위와 안내를 확인하세요.</p>;
  if (typeof value === "object") {
    if (value.row_id) return <blockquote>댓글 {value.number}: {value.text}</blockquote>;
    return <dl>{Object.entries(value).map(([key, item]) => <React.Fragment key={key}><dt><strong>{key}</strong></dt><dd><Result value={item} /></dd></React.Fragment>)}</dl>;
  }
  return <span>{typeof value === "boolean" ? (value ? "있음" : "없음") : String(value)}</span>;
}

export default function OpinionReport({ dataset, hasAI, autoGenerate = false }) {
  const [source, setSource] = useState("");
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const version = useRef(0);
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
    <p>저장한 댓글을 10개 항목으로 정리합니다. 먼저 댓글 AI 분석을 완료하면 주장·감정 결과가 채워집니다.</p>
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
    {report && <div aria-live="polite">{report.sections.map(section => <article key={section.number}>
      <h3>{section.number}. {section.title}</h3>
      <Result value={section.result} />
      <p className="research-help">{section.note}</p>
    </article>)}</div>}
  </section>;
}
