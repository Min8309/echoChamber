# EchoChamber 발표 자료

**주제:** 실제 댓글·리뷰를 정리하고 3~4인 가상 마을 토론의 정보 흐름을 비교하는 AI 실험 도구.

검토 소스: [`5b0ffce`](https://github.com/Min8309/echoChamber/tree/5b0ffce) · 작성일: 2026-10-27 (한국 기준).
설명은 이 커밋의 구현을 기준으로 하며 향후 제안은 별도로 표시했습니다.

## 파일

- [HTML 발표 자료](index.html): 이미지·스타일·발표 동작을 포함한 단일 파일. 다운로드 후 브라우저로 열면 오프라인에서도 내용을 볼 수 있습니다. 이전/다음 버튼, 좌우 방향키, 발표자 노트, 인쇄/PDF 저장 지원.
- [PPTX 편집본](EchoChamber.pptx): 16:9, 16장. 제목·본문·흐름·코드는 편집 가능한 텍스트와 도형입니다. 발표자 노트에 해석 범위와 코드 링크를 포함합니다.
- [PPT 호환본](EchoChamber.ppt): LibreOffice의 `MS PowerPoint 97` 필터로 변환한 실제 97–2003 바이너리입니다. 확장자만 바꾼 파일이 아닙니다. 구형 프로그램의 글꼴·줄바꿈 차이는 있을 수 있어 최신 환경에서는 PPTX를 권장합니다.
- [구조화된 원고](slides.json): 각 장의 주제·설명·코드 근거·발표자 노트.
- `assets/`: 임시 DB와 합성 댓글로 촬영한 화면. 실제 이용자 정보와 API 키를 포함하지 않습니다. 규칙 모드 화면이므로 AI 응답 품질을 보여주는 사례가 아닙니다.

발표 글꼴은 `Noto Sans CJK KR`입니다. 글꼴이 없는 환경에서는 시스템의 한국어 대체 글꼴을 사용합니다.

## 16장 구성

1. 프로젝트 핵심 주제와 기술 기반
2. 어떤 정보가 누구의 대화에서 달라지는가
3. 실제 자료에서 시각화까지 사용자 흐름
4. 정렬·검색·선별 워크스페이스
5. React–FastAPI–SQLite 시스템 구조
6. YouTube / K-HATERS / KOLD 수집 경로
7. 자료·실행·분석 데이터 계약과 접근 경계
8. 3~4인 토론 엔진과 실제 코드 발췌
9. 발화와 분석을 나누는 SSE 이벤트
10. Canvas 마을과 BFS 경로 탐색
11. 참여·자료 배정·대화 변화 시각화
12. 공통 AI 분석 계약과 지표 해석
13. SDK 호출 예산·비공개 자료·보존 기간
14. 주요 파일별 코드 지도
15. 테스트·실서비스 검증과 보장하지 않는 범위
16. 데모 시연 순서와 향후 확장 제안

## 코드 근거

| 책임 | 구현 | 핵심 내용 |
| --- | --- | --- |
| 화면 통합 | [main.jsx](../../frontend/src/main.jsx) | SSE 수신·분석 병합, 상태·기록·마을 연결 |
| 실제 자료 정리 | [RealDataLab.jsx](../../frontend/src/RealDataLab.jsx) | 수집·익명화 확인·정렬·검색·최대 10건 선별 |
| 공식 수집 | [collection.py](../../app/services/collection.py) | 고정 공급자 조회, 답글 관계, 가명화, 출처 서명, 외부 호출 제한 |
| 토론 실행 | [workbench.py](../../app/routers/workbench.py) | 원본 자료 확인, 3~4인 배정, 최근 4개 발언, 전체 선택 자료, 생성·분석·저장 |
| 분석 계약 | [text_analysis.py](../../app/services/text_analysis.py) · [analysis.py](../../app/models/analysis.py) | 실제/가상 텍스트의 공통 Pydantic 분류, `text-v1` |
| 실행 저장 | [runs.py](../../app/services/runs.py) | SQLite 스냅샷, 비공개 owner 조회, 원자적 완료 저장 |
| 시각화 | [DiscussionResults.jsx](../../frontend/src/DiscussionResults.jsx) · [Comparison.jsx](../../frontend/src/Comparison.jsx) | 발언·자료 배정·AI 감정·단계 지표, 선택 원문 대비 비교 |
| 마을 | [VillageScene.jsx](../../frontend/src/VillageScene.jsx) · [town.js](../../frontend/src/village/town.js) | 이벤트와 이동·말풍선 동기화, 24×18 타일, BFS |
| 내보내기 | [datasets.py](../../app/routers/datasets.py) · [research_report.py](../../app/services/research_report.py) | CSV 행 내보내기, JSON/HTML 분석·선택한 비교 결과 |
| 비용·접근 | [limits.py](../../app/services/limits.py) · [data_access.py](../../app/services/data_access.py) | 원자적 호출 시도 집계, 접근 키 해시, 비공개 조회 |

## 기술적으로 구분할 점

- SSE는 **토큰 단위가 아닌 완성된 발화와 분석 이벤트**입니다.
- OpenAI는 단계당 생성 1회 + 의미 분석 1회입니다. 규칙 모드는 AI 생성·분석으로 표시하지 않습니다.
- 묶음 토론은 자료 요약·근거 점검·다른 관점·종합 정리 과제를 순환합니다. 4번째 인물은 실행 전용 가상 자료 검토자입니다.
- 최대 30건을 저장하고 토론에는 최대 10건을 선택합니다. 선택 자료 순서와 분석·출처를 실행에 고정합니다.
- 신뢰도는 인물 수용 성향에 기반한 감쇠값이고, 문자열 변화율은 첫 자료와의 텍스트 차이입니다. 사실 검증·모델 정확도·인과관계 지표가 아닙니다.
- AI 직접 비교에는 양쪽 분석 완료와 같은 모델·분석 버전이 필요합니다. 공격성 참고 라벨은 가십 정답과 다릅니다.
- 접근 키는 로컬 브라우저의 capability입니다. 계정 인증이나 저장 데이터 암호화가 아닙니다.
- 공개 API라는 사실이 재사용 권한 전체를 보장하지 않습니다. YouTube 정책과 자료별 이용 조건을 확인해야 합니다.
- SQLite 영속 디스크가 없는 무료 배포에서는 재배포 시 기록이 사라질 수 있습니다.

## 재생성

발표 생성용 도구는 앱의 런타임 의존성에 추가하지 않았습니다.

```bash
uv pip install --python .venv/bin/python python-pptx==1.0.2
npm --prefix frontend run build
# requirements-dev.txt의 Playwright 및 시스템 Chromium 필요
.venv/bin/python scripts/capture_presentation.py
.venv/bin/python scripts/build_presentation.py
# LibreOffice가 설치된 환경에서 실제 .ppt 호환본 생성
soffice --headless --convert-to 'ppt:MS PowerPoint 97' \
  --outdir docs/presentation docs/presentation/EchoChamber.pptx
```

생성기와 캡처 스크립트: [build_presentation.py](../../scripts/build_presentation.py),
[capture_presentation.py](../../scripts/capture_presentation.py).

## 검증 범위

작성 시 서버 테스트 **34개**, Node 테스트 **10개** 통과를 다시 확인했습니다.
기존 브라우저 검증은 수집·분석·복구·다운로드·모바일과 4인 토론 흐름을 다룹니다.
발표 파일은 16장 PPTX·실제 PPT 변환·슬라이드 렌더링·HTML 모바일/발표 동작을 확인했습니다.
실제 OpenAI 응답 품질, 실제 YouTube 키의 유효성, 대규모 처리 성능의 평가 수치로 사용하면 안 됩니다.

## 외부 자료와 표시

- [K-HATERS 공식 저장소](https://github.com/ssu-humane/K-HATERS), CC BY 4.0. Park, Chaewon; Kim, Suhwan; Park, Kyubyong; Park, Kunwoo (2023), *K-HATERS: A Hate Speech Detection Corpus in Korean with Target-Specific Ratings*, Findings of EMNLP 2023. 앱에서 선택·가명화·편집할 수 있으며 발표 캡처는 원문 데이터가 아닌 합성 예시입니다.
- [KOLD 공식 저장소](https://github.com/boychaboy/KOLD), Jeong et al. (2022), *KOLD: A Large-scale Korean Offensive Language Dataset*. 명시적인 재배포 범위를 확인하지 못해 자동 수집과 데이터 번들을 제공하지 않습니다.
- [YouTube API 문서](https://developers.google.com/youtube/v3/docs/commentThreads/list), [개발자 정책](https://developers.google.com/youtube/terms/developer-policies).
- Pixel Agents에서 이식한 코드·캐릭터 자산은 [기존 MIT 고지](../../frontend/public/assets/pixel-agents/LICENSE.txt)를 유지합니다. 마을 캡처에도 해당 자산이 포함됩니다.
