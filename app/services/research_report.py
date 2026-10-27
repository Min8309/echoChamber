"""Self-contained, script-free HTML research report."""

from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo


def html_report(report):
    data, comparison = report["dataset"], report.get("comparison")
    exported_time = (
        datetime.fromisoformat(report["exported_at"])
        .astimezone(ZoneInfo("Asia/Seoul"))
        .strftime("%Y-%m-%d %H:%M:%S KST")
    )

    def text(value):
        return escape(str(value)) if value is not None else "—"

    def chart(label, real, virtual=None, unit="", percentage=False):
        scale = 100 if percentage else max(real or 0, virtual or 0, 1)
        bars = []
        for name, value, color in [
            ("실제 데이터", real, "#0d9488"),
            ("가상 대화", virtual, "#3366cc"),
        ]:
            if value is None:
                continue
            width = max(0, min(100, value / scale * 100))
            bars.append(
                f'<div class="bar-row"><span>{name}</span><div class="track"><i style="width:{width:.2f}%;background:{color}"></i></div><strong>{text(value)}{unit}</strong></div>'
            )
        return (
            f'<section class="metric"><h3>{text(label)}</h3>{"".join(bars)}</section>'
        )

    basic = (
        comparison["basic"] if comparison else {"real": data["basic"], "virtual": {}}
    )
    charts = "".join(
        chart(label, basic["real"][key], basic["virtual"].get(key), unit, percent)
        for key, label, unit, percent in [
            ("count", "표본 수", "건", False),
            ("average_length", "평균 글자 수", "자", False),
            ("question_pct", "질문 표현 비율", "%", True),
            ("uncertain_expression_pct", "전언·추측 표현 비율", "%", True),
        ]
    )
    if comparison and comparison["ai"]["comparable"]:
        ai = comparison["ai"]
        charts += "".join(
            chart(label, ai["real"][key], ai["virtual"][key], "%", True)
            for key, label in [
                ("gossip_pct", "AI 가십 분류 비율"),
                ("speculation_pct", "AI 추측 분류 비율"),
                ("negative_pct", "AI 부정 감정 비율"),
            ]
        )
        charts += f"<p>평균 평판 영향 (−1~1): 실제 {text(ai['real']['average_reputation_impact'])} · 가상 {text(ai['virtual']['average_reputation_impact'])}</p>"
    rows = []
    for row in data["rows"]:
        analysis = row.get("analysis")
        result = (
            "AI 미분석"
            if not analysis
            else f"{'가십' if analysis['is_gossip'] else '일반 내용'} · 감정: {analysis['sentiment']} · 확실성: {analysis['certainty']} · 평판 영향: {analysis['reputation_impact']}"
        )
        reference = (
            ""
            if not row.get("reference_labels")
            else "참고 연구 주석 (가십 분석과 별도): " + str(row["reference_labels"])
        )
        rows.append(
            f'<tr><td>{row["number"]}</td><td>{text(row["author"])}</td><td class="content">{text(row["text"])}</td><td>{text(row["status"])}</td><td>{text(result)}<p>{text(reference)}</p><p>{text(analysis.get("reason") if analysis else row.get("error"))}</p></td></tr>'
        )
    compare_note = (
        f"<p>비교한 가상 실행: {text(comparison['topic'])}</p><p>{text(comparison['note'])}</p>"
        if comparison
        else "<p>가상 마을 실행은 선택되지 않았습니다. 실제 데이터의 기초 지표만 표시합니다.</p>"
    )
    basis = (
        "비교 그래프는 저장된 데이터 전체를 기준으로 계산합니다."
        if comparison
        else "그래프는 내보낸 행을 기준으로 계산합니다."
    )
    origin = data.get("origin") or {}
    source_note = ""
    if origin:
        source_note = f'<section class="note"><h2>자료 출처·이용 조건</h2><p>{text(origin.get("name"))} · {text(origin.get("license"))}</p><p>{text(origin.get("source_url"))}</p><p>{text(origin.get("attribution"))}</p><p>변경 사항: {text(origin.get("changes"))}</p></section>'
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>EchoChamber 분석 보고서</title><style>body{{font-family:system-ui,sans-serif;color:#1e293b;background:#f8fafc;margin:0;padding:32px;line-height:1.7}}main{{max-width:1100px;margin:auto;background:white;padding:32px;border:1px solid #e2e8f0;border-radius:12px}}h1{{color:#204fa6}}h2{{margin-top:32px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.metric{{border:1px solid #e2e8f0;border-radius:8px;padding:16px}}h3{{font-size:14px;margin-top:0}}.bar-row{{display:flex;align-items:center;gap:10px;font-size:12px;margin:8px 0}}.bar-row span{{min-width:72px}}.bar-row strong{{min-width:65px;text-align:right}}.track{{background:#edf2f7;flex:1;height:12px}}i{{height:12px;display:block}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid #e2e8f0;text-align:left;padding:10px;vertical-align:top;overflow-wrap:anywhere}}th{{background:#f1f5f9}}.content{{white-space:pre-wrap;min-width:150px}}.table{{overflow-x:auto}}.note{{color:#64748b;font-size:12px}}@media(max-width:650px){{body,main{{padding:14px}}.grid{{grid-template-columns:1fr}}}}@media print{{body{{background:white;padding:0}}main{{border:0;padding:0}}.metric{{break-inside:avoid}}}}</style></head><body><main><p>EchoChamber · 실제 데이터 연구실</p><h1>{text(data["title"])}</h1><p>자료 종류: {"댓글" if data["source"] == "comment" else "리뷰"} · 내보낸 시각: {text(exported_time)}</p><p>전체 저장 {report["total_dataset_rows"]}건 · 내보낸 {len(data["rows"])}건 · AI 완료 {data["ai"]["analysed"]}건 · 범위: {"AI 완료 행만" if report["completed_only"] else "전체 행(미완료 구분)"}</p>{source_note}<h2>요약 그래프·수치</h2>{compare_note}<div class="grid">{charts}</div><p class="note">{basis} 기초 지표는 문자열 규칙이며 감정·사실성·왜곡 판정이 아닙니다. 표본 크기가 다를 수 있으며 인과관계를 입증하지 않습니다.</p><h2>행별 분석 결과</h2><div class="table"><table><thead><tr><th>행</th><th>가명 작성자</th><th>익명화 내용</th><th>상태</th><th>AI 분석</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="note">{text(report["notice"])}</p></main></body></html>"""
