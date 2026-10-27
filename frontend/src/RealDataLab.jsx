import React, { useEffect, useRef, useState } from "react";
import { previewCSV, previewTexts } from "./csv.mjs";
import { researchApi, dataHeaders, analyzeDataset } from "./dataApi.js";
import { ComparisonResults } from "./Comparison.jsx";

export default function RealDataLab({
  active,
  runs,
  engines,
  onVillage,
  villageBusy,
  onDeleted,
}) {
  const [manualText, setManualText] = useState("");
  const [preview, setPreview] = useState(null),
    [title, setTitle] = useState("실제 데이터 실험"),
    [source, setSource] = useState("comment"),
    [reviewed, setReviewed] = useState(false);
  const [dataset, setDataset] = useState(null),
    [history, setHistory] = useState([]),
    [availableRuns, setAvailableRuns] = useState(runs),
    [runId, setRunId] = useState("");
  const [comparison, setComparison] = useState(null),
    [busy, setBusy] = useState(false),
    [analysing, setAnalysing] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [exportFormat, setExportFormat] = useState("csv"),
    [completedOnly, setCompletedOnly] = useState(false);
  const controller = useRef(null),
    version = useRef(0);
  const hasAI = engines.includes("openai");
  const selected = preview?.rows.filter((row) => row.selected) || [];
  useEffect(() => {
    setAvailableRuns(runs);
  }, [runs]);
  useEffect(() => {
    if (active) refresh();
  }, [active]);
  useEffect(() => () => controller.current?.abort(), []);

  async function refresh() {
    try {
      const [saved, workbench] = await Promise.all([
        researchApi("/datasets"),
        researchApi("/runs"),
      ]);
      setHistory(saved);
      setAvailableRuns(workbench);
    } catch (err) {
      setError(err.message);
    }
  }
  async function openFile(event) {
    setError("");
    setNotice("");
    setReviewed(false);
    setPreview(null);
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 1024 * 1024) {
      setError("CSV는 1MB 이하로 준비해 주세요.");
      return;
    }
    try {
      const parsed = previewCSV(
        new TextDecoder("utf-8", { fatal: true }).decode(
          await file.arrayBuffer(),
        ),
      );
      setPreview(parsed);
      setNotice(
        `${parsed.total}건 중 ${parsed.rows.length}건을 브라우저에서 미리 봅니다. 아직 서버로 업로드하지 않았습니다.`,
      );
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "CSV를 UTF-8 형식으로 저장한 뒤 다시 선택해 주세요."
          : err.message,
      );
    }
    event.target.value = "";
  }
  function previewManual() {
    setError("");
    setReviewed(false);
    try {
      setPreview(previewTexts(manualText));
      setManualText("");
      setNotice(
        "직접 입력한 문장을 브라우저에서 가림 처리했습니다. 아직 서버로 전송하지 않았습니다. 내용을 확인한 뒤 저장해 주세요.",
      );
    } catch (err) {
      setError(err.message);
    }
  }
  function editRow(id, patch) {
    setReviewed(false);
    setPreview((previous) => ({
      ...previous,
      rows: previous.rows.map((row) =>
        row.local_id === id ? { ...row, ...patch } : row,
      ),
    }));
  }
  async function save() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const rows = selected.map(({ selected, ...row }) => row);
      const saved = await researchApi("/datasets", {
        method: "POST",
        body: JSON.stringify({ title, source, reviewed, rows }),
      });
      setDataset(saved);
      setComparison(null);
      setPreview(null);
      setReviewed(false);
      setNotice(
        "익명화 확인된 데이터가 저장됐고 기초 지표가 계산됐습니다. AI 분석은 별도 실행합니다.",
      );
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function open(id) {
    const request = ++version.current;
    setBusy(true);
    setError("");
    setComparison(null);
    try {
      const data = await researchApi(`/datasets/${id}`);
      if (request === version.current) setDataset(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function analyze() {
    controller.current = new AbortController();
    setAnalysing(true);
    setError("");
    setNotice("");
    setComparison(null);
    try {
      await analyzeDataset(
        dataset.dataset_id,
        controller.current.signal,
        setDataset,
      );
      setNotice(
        "분석 요청이 끝났습니다. 완료 건수와 행별 상태를 확인해 주세요.",
      );
    } catch (err) {
      if (err.name === "AbortError")
        setNotice(
          "중단 요청을 보냈습니다. 현재 처리 중인 한 행은 저장·과금될 수 있습니다. 결과 새로고침 후 이어서 분석할 수 있습니다.",
        );
      else setError(err.message);
    } finally {
      controller.current = null;
      setAnalysing(false);
      await refresh();
    }
  }
  async function compare() {
    setBusy(true);
    setError("");
    try {
      setComparison(
        await researchApi(
          `/datasets/${dataset.dataset_id}/compare?run_id=${encodeURIComponent(runId)}`,
        ),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    const format = exportFormat;
    setBusy(true);
    setError("");
    try {
      const query = new URLSearchParams({
        format,
        completed_only: String(completedOnly),
      });
      if (comparison) query.set("run_id", comparison.run_id);
      const response = await fetch(
        `/api/datasets/${dataset.dataset_id}/export?${query}`,
        { headers: dataHeaders(true) },
      );
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "다운로드에 실패했습니다.",
        );
      }
      const blob = await response.blob(),
        url = URL.createObjectURL(blob),
        link = document.createElement("a");
      link.href = url;
      link.download = `echochamber-analysis.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (villageBusy) return;
    if (
      !window.confirm("이 데이터와 연결한 비공개 마을 실험을 함께 삭제할까요?")
    )
      return;
    setBusy(true);
    setError("");
    try {
      await researchApi(`/datasets/${dataset.dataset_id}`, {
        method: "DELETE",
      });
      onDeleted?.(dataset.dataset_id);
      setDataset(null);
      setComparison(null);
      setNotice("데이터와 연결 실험을 삭제했습니다.");
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  const locked = busy || analysing;
  return (
    <div className="research-lab">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ECHOCHAMBER / REAL DATA LAB</div>
          <h1>실제 데이터 비교 연구실</h1>
          <p>실제 댓글·리뷰를 익명화해 분석하고 가상 마을 실험과 연결하세요.</p>
        </div>
        <span className="mode-tag">기존 마을 화면 유지</span>
      </div>
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert success" role="status">
          {notice}
        </div>
      )}
      <section className="panel research-upload">
        <div className="section-heading">
          <h2>1. 실제 댓글·리뷰 입력 · CSV 업로드</h2>
          <span className="caption">최대 1MB · 한 번에 30건</span>
        </div>
        <div className="research-fields">
          <label>
            데이터 이름
            <input
              aria-label="데이터 이름"
              value={title}
              maxLength={100}
              disabled={locked}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            데이터 종류
            <select
              aria-label="데이터 종류"
              value={source}
              disabled={locked}
              onChange={(event) => setSource(event.target.value)}
            >
              <option value="comment">실제 댓글</option>
              <option value="review">제품·서비스 리뷰</option>
            </select>
          </label>
          <label className="research-file">
            CSV 파일
            <input
              aria-label="댓글·리뷰 CSV 파일"
              type="file"
              accept=".csv,text/csv"
              disabled={locked}
              onChange={openFile}
            />
          </label>
        </div>
        <p className="research-help">
          필수 열: text 또는 내용. 선택 열: author_id, thread_id, message_id,
          reply_to_id, rating(0~5), created_at. UTF-8 CSV를 사용하세요. 파일은
          브라우저에서 읽고, 선택·확인한 문장만 서버에 저장합니다.
        </p>
        <p className="research-help">
          <a className="text-button" href="/sample-reviews.csv" download>
            CSV 양식 예시 다운로드 (실제 수집 자료 아님)
          </a>
        </p>
        <div className="research-manual">
          <label>
            실제 댓글·리뷰 직접 입력
            <textarea
              aria-label="실제 댓글·리뷰 직접 입력"
              value={manualText}
              maxLength={93000}
              disabled={locked}
              onChange={(event) => setManualText(event.target.value)}
              placeholder={
                "분석할 댓글이나 리뷰를 붙여 넣으세요.\n한 줄에 한 건씩, 최대 30건을 입력할 수 있습니다."
              }
            />
          </label>
          <p className="research-help">
            직접 입력도 미리보기에서 연락처를 가립니다. 미리보기 전 원문은
            서버로 보내지 않습니다.
          </p>
          <button
            type="button"
            className="primary"
            disabled={locked || !manualText.trim()}
            onClick={previewManual}
          >
            직접 입력 미리보기
          </button>
        </div>
        {preview && (
          <>
            <div className="research-preview">
              {preview.rows.map((row, index) => (
                <div className="research-preview-row" key={row.local_id}>
                  <label>
                    <input
                      type="checkbox"
                      aria-label={`${index + 1}행 선택`}
                      checked={row.selected}
                      disabled={locked}
                      onChange={(event) =>
                        editRow(row.local_id, {
                          selected: event.target.checked,
                        })
                      }
                    />
                    {index + 1}행 · {row.author || "익명"}
                  </label>
                  <textarea
                    aria-label={`${index + 1}행 익명화 내용`}
                    value={row.text}
                    maxLength={3000}
                    disabled={locked}
                    onChange={(event) =>
                      editRow(row.local_id, { text: event.target.value })
                    }
                  />
                </div>
              ))}
            </div>
            <p className="research-help">
              이메일·전화번호·링크 등을 자동 가림 처리하고 작성자 ID를 가명으로
              바꿉니다. 사람 이름·주소 등은 빠질 수 있으므로 내용을 직접
              수정하세요.
            </p>
            <label className="research-consent">
              <input
                type="checkbox"
                checked={reviewed}
                disabled={locked}
                onChange={(event) => setReviewed(event.target.checked)}
              />
              선택한 문장의 개인정보를 직접 확인했고, 저장·분석할 수 있는
              데이터입니다.
            </label>
            <div className="research-actions">
              <button
                className="primary"
                disabled={
                  locked ||
                  !reviewed ||
                  !selected.length ||
                  !title.trim() ||
                  selected.some((row) => !row.text.trim())
                }
                onClick={save}
              >
                선택한 {selected.length}건 저장 · 기초 분석
              </button>
            </div>
          </>
        )}
      </section>
      <section className="panel research-history">
        <div className="section-heading">
          <h2>이 브라우저의 데이터</h2>
          <button className="text-button" disabled={locked} onClick={refresh}>
            목록 새로고침
          </button>
        </div>
        <div className="research-saved">
          {history.length ? (
            history.map((item) => (
              <button
                key={item.dataset_id}
                disabled={locked}
                className={
                  dataset?.dataset_id === item.dataset_id ? "selected" : ""
                }
                onClick={() => open(item.dataset_id)}
              >
                {item.title}
                <small>
                  {item.count}건 · AI {item.analysed}건 완료
                </small>
              </button>
            ))
          ) : (
            <p className="research-help">저장된 데이터가 없습니다.</p>
          )}
        </div>
        <p className="research-help">
          접근 키는 이 사이트의 브라우저 저장소에 보관됩니다. 다른 브라우저나
          저장소 삭제 후에는 복구할 수 없습니다. 공유 PC에서 사용하지 마세요.
          무료 서버 재배포 시 데이터가 초기화될 수 있습니다.
        </p>
      </section>
      {dataset && (
        <>
          <section className="panel research-analysis">
            <div className="section-heading">
              <h2>2. 분석 결과 · 이어서 분석 · 다운로드</h2>
              <span className="caption">{dataset.title}</span>
            </div>
            <div className="research-summary">
              <div>
                <span>저장 문장</span>
                <strong>{dataset.basic.count}건</strong>
              </div>
              <div>
                <span>평균 글자 수</span>
                <strong>{dataset.basic.average_length}자</strong>
              </div>
              <div>
                <span>전언·추측 표현</span>
                <strong>{dataset.basic.uncertain_expression_pct}%</strong>
              </div>
              <div>
                <span>AI 분석 완료</span>
                <strong>
                  {dataset.ai.analysed}/{dataset.ai.total}건
                </strong>
              </div>
            </div>
            <p className="research-help">
              기초 지표는 문자열 규칙이며 AI 감정·가십 판정이 아닙니다. 선택
              데이터에 포함된 답글 연결은 {dataset.reply_pairs}쌍입니다. 독립
              댓글에서 전달 경로나 사실 왜곡을 추정하지 않습니다.
            </p>
            <div className="research-actions">
              <button
                className="primary"
                disabled={
                  locked || !hasAI || dataset.ai.analysed === dataset.ai.total
                }
                onClick={analyze}
              >
                {analysing
                  ? "AI 분석 중…"
                  : `AI 분석 / 이어서 분석 · 최대 ${dataset.ai.total - dataset.ai.analysed}회 호출`}
              </button>
              {analysing && (
                <button
                  className="stop-button"
                  onClick={() => controller.current?.abort()}
                >
                  실제 데이터 분석 중단
                </button>
              )}
              <button
                disabled={locked}
                onClick={() => open(dataset.dataset_id)}
              >
                결과 새로고침
              </button>
              <label className="export-format">
                다운로드 형식
                <select
                  aria-label="다운로드 형식"
                  value={exportFormat}
                  disabled={locked}
                  onChange={(event) => setExportFormat(event.target.value)}
                >
                  <option value="csv">CSV · 표 데이터</option>
                  <option value="json">JSON · 전체 구조·비교 수치</option>
                  <option value="html">HTML · 그래프 포함 보고서</option>
                </select>
              </label>
              <label className="export-scope">
                <input
                  type="checkbox"
                  checked={completedOnly}
                  disabled={locked}
                  onChange={(event) => setCompletedOnly(event.target.checked)}
                />
                AI 완료 행만
              </label>
              <button
                disabled={
                  locked || (completedOnly && dataset.ai.analysed === 0)
                }
                onClick={download}
              >
                분석 결과 다운로드
              </button>
              <button
                className="research-delete"
                disabled={locked || villageBusy}
                onClick={remove}
              >
                데이터 삭제
              </button>
            </div>
            {!hasAI && (
              <p className="research-help">
                현재 서버에는 AI 키가 없어 기초 분석·마을 연결·기초
                비교·CSV/JSON/HTML 다운로드를 사용할 수 있습니다. AI 의미 분석은
                Render에 API 키를 설정하면 활성화됩니다.
              </p>
            )}
            <div className="research-row-results">
              {dataset.rows.map((row) => (
                <article key={row.row_id}>
                  <div className="research-row-heading">
                    <strong>
                      {row.number}행 · {row.author}
                      {row.rating != null ? ` · ${row.rating}점` : ""}
                    </strong>
                    <span>
                      {row.analysis
                        ? "AI 완료"
                        : row.status === "processing"
                          ? "분석 중"
                          : row.status === "failed"
                            ? "재시도 가능"
                            : "AI 미분석"}
                    </span>
                  </div>
                  <p>{row.text}</p>
                  {row.analysis && (
                    <>
                      <div className="analysis-tags">
                        <span>
                          {row.analysis.is_gossip ? "가십" : "일반 내용"}
                        </span>
                        <span>
                          감정:{" "}
                          {
                            {
                              positive: "긍정",
                              neutral: "중립",
                              negative: "부정",
                            }[row.analysis.sentiment]
                          }
                        </span>
                        <span>
                          확실성:{" "}
                          {
                            {
                              confirmed: "확정 표현",
                              hearsay: "전언",
                              speculation: "추측",
                            }[row.analysis.certainty]
                          }
                        </span>
                        <span>평판 영향 {row.analysis.reputation_impact}</span>
                      </div>
                      <p className="research-reason">{row.analysis.reason}</p>
                    </>
                  )}
                  {row.error && <small>{row.error}</small>}
                  <button
                    className="text-button"
                    disabled={locked || villageBusy}
                    onClick={() =>
                      onVillage({
                        dataset_id: dataset.dataset_id,
                        dataset_row_id: row.row_id,
                        title: dataset.title,
                        text: row.text,
                        analysis: row.analysis,
                      })
                    }
                  >
                    이 문장으로 마을 실험 →
                  </button>
                </article>
              ))}
            </div>
          </section>
          <section className="panel research-comparison">
            <div className="section-heading">
              <h2>3. 가상 마을 실행과 그래프·수치 비교</h2>
            </div>
            <div className="research-fields">
              <label className="research-run-picker">
                비교할 가상 실행
                <select
                  aria-label="비교할 가상 실행"
                  value={runId}
                  disabled={locked}
                  onChange={(event) => {
                    setRunId(event.target.value);
                    setComparison(null);
                  }}
                >
                  <option value="">실행 기록을 선택하세요</option>
                  {availableRuns.map((item) => (
                    <option key={item.run_id} value={item.run_id}>
                      {item.topic.slice(0, 70)} · {item.completed_steps}단계
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="primary"
                disabled={locked || !runId}
                onClick={compare}
              >
                그래프·숫자로 비교
              </button>
            </div>
            <ComparisonResults result={comparison} />
            {comparison && (
              <p className="research-help">
                선택한 비교 수치는 JSON·HTML 다운로드에 함께 포함됩니다.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
