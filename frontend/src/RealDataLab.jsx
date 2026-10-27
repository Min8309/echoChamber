import React, { useEffect, useRef, useState } from "react";
import { previewCSV, previewTexts } from "./csv.mjs";
import { researchApi, dataHeaders, analyzeDataset } from "./dataApi.js";
import { ComparisonResults } from "./Comparison.jsx";
import SourceCollector from "./SourceCollector.jsx";
import { previewResearchFile } from "./researchImport.mjs";

export default function RealDataLab({
  active,
  linkedRun,
  runs,
  engines,
  onVillage,
  villageBusy,
  onDeleted,
}) {
  const [manualText, setManualText] = useState("");
  const [fileProvider, setFileProvider] = useState("csv"),
    [collecting, setCollecting] = useState(false);
  const [sortOrder, setSortOrder] = useState("original"),
    [query, setQuery] = useState(""),
    [discussionRows, setDiscussionRows] = useState([]),
    [participantCount, setParticipantCount] = useState(3);
  const sourceFile = useRef(null);
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
  const organisedRows = [...(dataset?.rows || [])].filter(
    (row) => !query.trim() || row.text.includes(query.trim()),
  );
  organisedRows.sort((a, b) =>
    sortOrder === "length"
      ? b.text.length - a.text.length
      : sortOrder === "negative"
        ? Number(b.analysis?.sentiment === "negative") -
          Number(a.analysis?.sentiment === "negative")
        : sortOrder === "rating"
          ? (b.rating ?? -1) - (a.rating ?? -1)
          : a.number - b.number,
  );
  useEffect(() => {
    setDiscussionRows(
      (dataset?.rows || []).slice(0, 10).map((row) => row.row_id),
    );
    setQuery("");
  }, [dataset?.dataset_id]);
  const selected = preview?.rows.filter((row) => row.selected) || [];
  useEffect(() => {
    setAvailableRuns(runs);
  }, [runs]);
  useEffect(() => {
    if (active) refresh();
  }, [active]);
  useEffect(() => {
    if (
      active &&
      dataset &&
      linkedRun?.source_data?.dataset_id === dataset.dataset_id
    ) {
      setRunId(linkedRun.run_id);
      setComparison(null);
    }
  }, [active, dataset?.dataset_id, linkedRun?.run_id]);
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
    if (
      file.size >
      (/\.(json|jsonl)$/i.test(file.name) && fileProvider !== "csv"
        ? 100 * 1024 * 1024
        : 1024 * 1024)
    ) {
      setError(
        !/\.(json|jsonl)$/i.test(file.name) || fileProvider === "csv"
          ? "CSV는 1MB 이하로 준비해 주세요."
          : "연구 JSON 파일은 100MB 이하입니다. 처음 30건만 읽습니다.",
      );
      return;
    }
    try {
      const parsed =
        /\.(json|jsonl)$/i.test(file.name) && fileProvider !== "csv"
          ? await previewResearchFile(file, fileProvider)
          : {
              ...previewCSV(
                new TextDecoder("utf-8", { fatal: true }).decode(
                  await file.arrayBuffer(),
                ),
              ),
              file_provider: fileProvider === "csv" ? null : fileProvider,
            };
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
        body: JSON.stringify({
          title,
          source,
          reviewed,
          rows,
          collection_token: preview.collection_token || null,
          file_provider: preview.file_provider || null,
        }),
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
  const locked = busy || analysing || collecting;
  return (
    <div className="research-lab">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ECHOCHAMBER / REAL DATA LAB</div>
          <h1>실제 데이터 비교 연구실</h1>
          <p>
            실제 댓글이 마을의 이야기가 됩니다. 데이터를 가져오고, AI 에이전트가
            전달하는 과정을 관찰하세요.
          </p>
        </div>
        <span className="mode-tag">REAL DATA → SMALLVILLE</span>
      </div>
      <section
        className="research-journey panel"
        aria-label="실제 데이터에서 가상 마을까지"
      >
        <div className="research-journey-intro">
          <div className="eyebrow">FROM COMMENTS TO CONVERSATIONS</div>
          <h2>실제 목소리를, 가상 마을에서 실험하세요.</h2>
          <p>
            댓글·리뷰의 표현과 맥락을 분석한 뒤, 선택한 문장이 마을을 거치며
            어떻게 달라지는지 비교합니다.
          </p>
          <small>
            원문 분석과 가상 대화는 구분해서 표시합니다. 시뮬레이션은 실제
            여론이나 사실 여부를 증명하지 않습니다.
          </small>
        </div>
        <ol className="research-journey-steps">
          {[
            [
              "01",
              "실제 데이터 가져오기",
              "YouTube · K-HATERS · 파일 · 직접 입력",
              Boolean(dataset || preview),
            ],
            [
              "02",
              "익명화 · 내용 분석",
              "개인정보 확인 후 저장하고 지표 살펴보기",
              Boolean(dataset),
            ],
            [
              "03",
              "가상 마을에 전달",
              "분석 결과의 문장 하나를 실험 시작점으로 선택",
              Boolean(
                dataset &&
                  linkedRun?.source_data?.dataset_id === dataset.dataset_id,
              ),
            ],
            [
              "04",
              "그래프 비교 · 다운로드",
              "실제 원문과 전달 결과의 수치 비교",
              Boolean(comparison),
            ],
          ].map(([number, title, description, ready]) => (
            <li key={number} className={ready ? "ready" : ""}>
              <span className="journey-number">{number}</span>
              <div>
                <strong>{title}</strong>
                <p>{description}</p>
                <small>{ready ? "진행됨" : "다음 단계"}</small>
              </div>
            </li>
          ))}
        </ol>
      </section>
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
      <SourceCollector
        active={active}
        locked={locked}
        onBusy={setCollecting}
        onPreview={(result) => {
          setPreview(result);
          setReviewed(false);
          setSource("comment");
          setTitle(`${result.origin.name} · ${result.rows.length}건`);
          setNotice(
            "공식 자료를 가명화해 가져왔습니다. 아직 데이터셋으로 저장하지 않았습니다. 내용·출처를 확인해 주세요.",
          );
          setError("");
        }}
        onChooseFile={(provider) => {
          setFileProvider(provider);
          if (sourceFile.current) {
            sourceFile.current.accept = ".json,.jsonl,.csv";
            sourceFile.current.click();
          }
        }}
      />
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
          <label>
            파일 양식
            <select
              aria-label="연구 파일 양식"
              value={fileProvider}
              disabled={locked}
              onChange={(event) => setFileProvider(event.target.value)}
            >
              <option value="csv">일반 CSV</option>
              <option value="khaters">K-HATERS JSON/JSONL/CSV</option>
              <option value="kold">KOLD JSON/CSV</option>
            </select>
          </label>
          <label className="research-file">
            CSV 파일
            <input
              aria-label="댓글·리뷰 CSV 파일"
              ref={sourceFile}
              type="file"
              accept={
                fileProvider === "csv" ? ".csv,text/csv" : ".json,.jsonl,.csv"
              }
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
            {preview.origin && (
              <div className="source-attribution">
                <strong>
                  출처: {preview.origin.name} · {preview.origin.license}
                </strong>
                <p>{preview.origin.attribution}</p>
                <p>{preview.origin.changes}</p>
                {preview.origin.truncated && (
                  <p>수집 한도로 일부 댓글만 포함됩니다.</p>
                )}
              </div>
            )}
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
            {dataset.origin && (
              <div className="source-attribution">
                <strong>출처: {dataset.origin.name}</strong>
                <p>{dataset.origin.attribution}</p>
                <a
                  href={dataset.origin.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  공식 출처 ↗
                </a>{" "}
                · {dataset.origin.license}
                <p>{dataset.origin.changes}</p>
                {dataset.origin.expires_at && (
                  <p>
                    만료 예정:{" "}
                    {new Date(dataset.origin.expires_at * 1000).toLocaleString(
                      "ko-KR",
                      { timeZone: "Asia/Seoul" },
                    )}
                    . 만료 시 자료와 연결 실험을 함께 삭제합니다.
                  </p>
                )}
              </div>
            )}
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
            <div className="research-village-handoff">
              <span aria-hidden="true">◎</span>
              <div>
                <h3>분석한 문장을 마을로 보내세요</h3>
                <p>
                  아래에서 자료를 정렬·선별하고 ‘마을 토론 준비’를 선택하세요.
                  한 문장 전달 실험도 가능합니다. 마을 화면에서 전달 단계와 실행
                  모드를 정하고 실행한 뒤, 이곳으로 돌아와 그래프를 비교할 수
                  있습니다.
                </p>
                <small>
                  AI 의미 분석은 OpenAI 키가 필요합니다. 규칙 기반 실험은 AI
                  분석과 구분해 표시합니다.
                </small>
              </div>
            </div>
            <section
              className="discussion-preparation"
              aria-label="자료 정렬과 토론 준비"
            >
              <h3>자료 정렬 · 선별 → 3~4인 마을 토론</h3>
              <p>
                정렬한 목록에서 최대 10건을 고르세요. 선택한 자료 전체를 토론에
                제공하고, 인물이 돌아가며 요약·근거 점검·다른 관점·종합 정리를
                진행합니다.
              </p>
              <div className="research-fields">
                <label>
                  정보 정렬
                  <select
                    aria-label="정보 정렬"
                    value={sortOrder}
                    onChange={(event) => setSortOrder(event.target.value)}
                  >
                    <option value="original">수집 순서</option>
                    <option value="length">긴 문장 먼저</option>
                    <option value="negative">AI 부정 감정 먼저</option>
                    <option value="rating">별점 높은 순</option>
                  </select>
                </label>
                <label>
                  문장 검색
                  <input
                    aria-label="자료 문장 검색"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="검색어로 자료 찾기"
                  />
                </label>
                <label>
                  토론 인원
                  <select
                    aria-label="토론 인원"
                    value={participantCount}
                    disabled={locked || villageBusy}
                    onChange={(event) =>
                      setParticipantCount(Number(event.target.value))
                    }
                  >
                    <option value="3">3명 · 마을 인물</option>
                    <option value="4">4명 · 가상 자료 검토자 포함</option>
                  </select>
                </label>
                <button
                  type="button"
                  disabled={locked}
                  onClick={() =>
                    setDiscussionRows(
                      organisedRows.slice(0, 10).map((row) => row.row_id),
                    )
                  }
                >
                  현재 목록 앞 10건 선택
                </button>
                <button
                  type="button"
                  className="primary"
                  disabled={locked || villageBusy || !discussionRows.length}
                  onClick={() => {
                    const rows = organisedRows.filter((row) =>
                      discussionRows.includes(row.row_id),
                    );
                    const hidden = dataset.rows.filter(
                      (row) =>
                        discussionRows.includes(row.row_id) &&
                        !rows.some((item) => item.row_id === row.row_id),
                    );
                    const chosen = [...rows, ...hidden];
                    onVillage({
                      dataset_id: dataset.dataset_id,
                      dataset_row_ids: chosen.map((row) => row.row_id),
                      participant_count: participantCount,
                      title: dataset.title,
                      text: chosen[0].text,
                      rows: chosen,
                      discussion: true,
                    });
                  }}
                >
                  선택한 {discussionRows.length}건으로 마을 토론 준비 →
                </button>
              </div>
              <small>
                검색은 선택을 해제하지 않습니다. 선택 자료는 토론 시작 시
                스냅샷으로 저장합니다.{" "}
                {hasAI
                  ? "OpenAI를 선택하면 실제 AI 대화 생성·분석을 수행합니다."
                  : "현재 AI 키가 없어 규칙 템플릿으로 동선을 실험할 수 있습니다. AI 토론에는 OpenAI 키가 필요합니다."}
              </small>
            </section>
            <div className="research-row-results">
              {organisedRows.map((row) => (
                <article key={row.row_id}>
                  <label className="discussion-select">
                    <input
                      type="checkbox"
                      aria-label={`${row.number}행 토론 자료 선택`}
                      checked={discussionRows.includes(row.row_id)}
                      disabled={
                        locked ||
                        villageBusy ||
                        (!discussionRows.includes(row.row_id) &&
                          discussionRows.length >= 10)
                      }
                      onChange={(event) =>
                        setDiscussionRows((previous) =>
                          event.target.checked
                            ? [...previous, row.row_id]
                            : previous.filter((id) => id !== row.row_id),
                        )
                      }
                    />
                    토론 자료 포함
                  </label>
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
                  {Object.keys(row.reference_labels || {}).length > 0 && (
                    <p className="research-reference">
                      입력 자료의 참고 라벨 (AI 가십 분석과 별도):{" "}
                      {JSON.stringify(row.reference_labels)}
                    </p>
                  )}
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
