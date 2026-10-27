import React, { useEffect, useState } from "react";
import { researchApi } from "./dataApi.js";

export default function SourceCollector({
  active,
  locked,
  onBusy,
  onPreview,
  onChooseFile,
}) {
  const [catalog, setCatalog] = useState(null),
    [provider, setProvider] = useState("khaters"),
    [video, setVideo] = useState(""),
    [limit, setLimit] = useState(20),
    [replies, setReplies] = useState(true),
    [split, setSplit] = useState("test"),
    [offset, setOffset] = useState(0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    if (active && !catalog)
      researchApi("/collection/sources")
        .then(setCatalog)
        .catch((err) => setError(err.message));
  }, [active]);
  async function collect() {
    setBusy(true);
    onBusy(true);
    setError("");
    try {
      const result = await researchApi("/collection/preview", {
        method: "POST",
        body: JSON.stringify({
          provider,
          video,
          limit: Number(limit),
          include_replies: replies,
          split,
          offset: Number(offset),
        }),
      });
      onPreview(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      onBusy(false);
    }
  }
  const disabled = locked || busy;
  return (
    <section className="panel source-collector">
      <div className="section-heading">
        <h2>0. 공식 API · 공개 연구 댓글 가져오기</h2>
        <span className="caption">웹페이지 크롤링 없이 연결</span>
      </div>
      <div className="source-cards">
        <article>
          <strong>YouTube 공식 API</strong>
          <p>
            영상의 공개 댓글과 답글을 가져옵니다. 답글은 실제 부모 댓글에
            연결하며, 설정한 건수까지만 수집합니다.
          </p>
          <small>
            {catalog?.youtube_configured
              ? "서버 API 키 설정됨"
              : "Render 환경 변수 YOUTUBE_API_KEY 설정 필요"}
          </small>
          <a
            href="https://developers.google.com/youtube/v3/docs/commentThreads/list"
            target="_blank"
            rel="noreferrer"
          >
            공식 API 안내 ↗
          </a>
        </article>
        <article>
          <strong>K-HATERS · CC BY 4.0</strong>
          <p>
            공식 Hugging Face 배포에서 연구 댓글 표본을 가져옵니다. 원본
            공격성·표적 라벨과 AI 가십 분석은 별도입니다.
          </p>
          <a
            href="https://github.com/ssu-humane/K-HATERS"
            target="_blank"
            rel="noreferrer"
          >
            공식 저장소·이용 조건 ↗
          </a>
        </article>
        <article>
          <strong>KOLD · 공식 파일 가져오기</strong>
          <p>
            공식 JSON 파일을 확보해 불러옵니다. 별도 라이선스 범위를 확인하지
            못해 서버 자동 재배포는 연결하지 않았습니다.
          </p>
          <button
            className="text-button"
            disabled={disabled}
            onClick={() => onChooseFile("kold")}
          >
            KOLD JSON 파일 선택
          </button>
          <a
            href="https://github.com/boychaboy/KOLD"
            target="_blank"
            rel="noreferrer"
          >
            공식 배포·이용 안내 ↗
          </a>
        </article>
      </div>
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      <div className="research-fields">
        <label>
          수집 경로
          <select
            aria-label="댓글 수집 경로"
            value={provider}
            disabled={disabled}
            onChange={(e) => setProvider(e.target.value)}
          >
            <option value="khaters">K-HATERS 연구 댓글</option>
            <option value="youtube">YouTube 공식 API</option>
          </select>
        </label>
        {provider === "youtube" ? (
          <label className="research-run-picker">
            영상 주소 또는 ID
            <input
              aria-label="YouTube 영상 주소"
              value={video}
              maxLength={500}
              disabled={disabled}
              onChange={(e) => setVideo(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
            />
          </label>
        ) : (
          <>
            <label>
              데이터 분할
              <select
                aria-label="K-HATERS 분할"
                value={split}
                disabled={disabled}
                onChange={(e) => setSplit(e.target.value)}
              >
                <option value="test">test</option>
                <option value="validation">validation</option>
                <option value="train">train</option>
              </select>
            </label>
            <label>
              시작 위치
              <input
                type="number"
                min="0"
                max="190000"
                aria-label="연구 댓글 시작 위치"
                value={offset}
                disabled={disabled}
                onChange={(e) => setOffset(e.target.value)}
              />
            </label>
          </>
        )}
        <label>
          최대 건수
          <input
            type="number"
            min="1"
            max="30"
            aria-label="수집 최대 건수"
            value={limit}
            disabled={disabled}
            onChange={(e) => setLimit(e.target.value)}
          />
        </label>
        <button
          className="primary"
          type="button"
          disabled={
            disabled ||
            !catalog ||
            Number(limit) < 1 ||
            Number(limit) > 30 ||
            (provider === "youtube" &&
              (!catalog.youtube_configured || !video.trim()))
          }
          onClick={collect}
        >
          {busy ? "공식 자료 가져오는 중…" : "공식 자료 수집 · 미리보기"}
        </button>
      </div>
      {provider === "youtube" && (
        <label className="research-consent">
          <input
            type="checkbox"
            checked={replies}
            disabled={disabled}
            onChange={(e) => setReplies(e.target.checked)}
          />
          답글 포함 (commentThreads + comments)
        </label>
      )}
      <p className="research-help">
        수집 시 AI 호출은 하지 않습니다. 가명화된 미리보기를 확인한 뒤 선택한
        행만 저장합니다. 공개 API도 별도 이용 정책을 따릅니다. YouTube 자료는
        최대 30일 이내 만료 처리하며, 다시 사용하려면 새로 수집하세요. 연구
        데이터에는 불쾌한 표현이 포함될 수 있습니다.
      </p>
    </section>
  );
}
