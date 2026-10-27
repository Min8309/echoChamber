import React, { useEffect, useState } from "react";
import { researchApi } from "./dataApi.js";

function Pair({ label, real, virtual, unit = "", fixed = false }) {
  const max = fixed ? 100 : Math.max(real || 0, virtual || 0, 1);
  return (
    <article className="comparison-metric">
      <h3>{label}</h3>
      {[
        ["실제 데이터", real, "real"],
        ["가상 대화", virtual, "virtual"],
      ].map(([name, value, type]) => (
        <div className="comparison-value" key={type}>
          <span>{name}</span>
          <div className="comparison-track">
            <i
              className={type}
              style={{
                width: `${value == null ? 0 : Math.max(0, (value / max) * 100)}%`,
              }}
            />
          </div>
          <strong>{value == null ? "—" : `${value}${unit}`}</strong>
        </div>
      ))}
    </article>
  );
}
export function ComparisonResults({ result }) {
  if (!result) return null;
  const { basic, ai } = result;
  return (
    <div
      className="comparison-results"
      aria-label="실제 데이터와 가상 대화 비교 결과"
    >
      <div className="comparison-legend">
        <span className="real-key" />
        실제 데이터
        {result.scope === "selected_materials"
          ? " (토론에 선택한 자료)"
          : ""}{" "}
        <span className="virtual-key" />
        가상 대화
      </div>
      <div className="comparison-grid">
        <Pair
          label="표본 수"
          real={basic.real.count}
          virtual={basic.virtual.count}
          unit="건"
        />
        <Pair
          label="평균 글자 수"
          real={basic.real.average_length}
          virtual={basic.virtual.average_length}
          unit="자"
        />
        <Pair
          label="질문 표현 비율"
          real={basic.real.question_pct}
          virtual={basic.virtual.question_pct}
          unit="%"
          fixed
        />
        <Pair
          label="전언·추측 표현 비율"
          real={basic.real.uncertain_expression_pct}
          virtual={basic.virtual.uncertain_expression_pct}
          unit="%"
          fixed
        />
      </div>
      <p className="research-help">
        위 수치는 같은 문자열 규칙으로 계산한 기초 지표이며 감정·사실성·왜곡
        판정이 아닙니다.
      </p>
      <div className="research-coverage">
        AI 분석 완료: 실제 {ai.real.analysed}/{ai.real.total}건 · 가상{" "}
        {ai.virtual.analysed}/{ai.virtual.total}건
      </div>
      {ai.comparable ? (
        <>
          <div className="comparison-grid">
            <Pair
              label="AI 가십 분류 비율"
              real={ai.real.gossip_pct}
              virtual={ai.virtual.gossip_pct}
              unit="%"
              fixed
            />
            <Pair
              label="AI 추측 분류 비율"
              real={ai.real.speculation_pct}
              virtual={ai.virtual.speculation_pct}
              unit="%"
              fixed
            />
            <Pair
              label="AI 부정 감정 비율"
              real={ai.real.negative_pct}
              virtual={ai.virtual.negative_pct}
              unit="%"
              fixed
            />
          </div>
          <p className="research-coverage">
            평균 평판 영향 (−1~1): 실제{" "}
            <strong>{ai.real.average_reputation_impact}</strong> · 가상{" "}
            <strong>{ai.virtual.average_reputation_impact}</strong>
          </p>
        </>
      ) : (
        <p className="research-help">
          AI 수치의 직접 비교는 양쪽 분석 완료와 동일한 모델·분석 버전이
          필요합니다. 규칙 모드의 대화에는 AI 의미 분석을 만들어 넣지 않습니다.
        </p>
      )}
      <p className="research-help">{result.note}</p>
    </div>
  );
}
export function LinkedResults({ run, active = true }) {
  const [result, setResult] = useState(null),
    [error, setError] = useState("");
  const dataset = run?.source_data?.dataset_id;
  useEffect(() => {
    let active = true;
    setResult(null);
    setError("");
    if (active && dataset && !run.pending)
      researchApi(
        `/datasets/${dataset}/compare?run_id=${encodeURIComponent(run.run_id)}`,
      )
        .then((data) => {
          if (active) setResult(data);
        })
        .catch((err) => {
          if (active) setError(err.message);
        });
    return () => {
      active = false;
    };
  }, [dataset, run?.run_id, run?.pending, active]);
  if (!dataset) return null;
  return (
    <section className="panel linked-results">
      <div className="section-heading">
        <h2>실제 데이터 ↔ 가상 마을 실험</h2>
        <span className="caption">{run.source_data.title}</span>
      </div>
      {error && (
        <p className="research-help" role="alert">
          {error}
        </p>
      )}
      {run.pending ? (
        <p className="research-help">
          실험 완료 후 실제 데이터와의 비교 그래프를 표시합니다.
        </p>
      ) : (
        <ComparisonResults result={result} />
      )}
    </section>
  );
}
