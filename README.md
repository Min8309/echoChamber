# EchoChamber · React + FastAPI 실험 도구

**실제 댓글·리뷰 수집 → 익명화·정렬·자료 선별 → 3~4인 가상 마을 토론 → 대화 흐름 분석·시각화**를 연결한 AI 실험 도구입니다.
실제 텍스트와 가상 대화를 같은 기준으로 비교하고, 자료 출처·실험 설정·결과를 함께 확인합니다.
파란색·흰색 대시보드와 Pixel Agents 기반 Canvas 마을을 유지하며, 단일 문장 전달 실험도 지원합니다.

## 프로젝트 발표 자료

**핵심 주제·기술 구조·주요 코드·검증 범위를 정리한 16장 자료입니다.** 검토 기준: `5b0ffce` (2026-10-27).

[배포 사이트에서 HTML 발표 바로 열기](https://echochamber-y3r4.onrender.com/presentation/) · [PPTX 다운로드](https://echochamber-y3r4.onrender.com/presentation/EchoChamber.pptx) · [PPT 다운로드](https://echochamber-y3r4.onrender.com/presentation/EchoChamber.ppt)

| 형식 | 자료 | 사용 방법 |
| --- | --- | --- |
| HTML | [발표 자료](docs/presentation/index.html) · [HTML 다운로드](https://raw.githubusercontent.com/Min8309/echoChamber/main/docs/presentation/index.html) | 저장 후 브라우저에서 열기. 이미지 포함 단일 파일, 방향키 이동·노트·인쇄 지원 |
| PPTX | [PowerPoint 편집본](docs/presentation/EchoChamber.pptx) · [다운로드](https://raw.githubusercontent.com/Min8309/echoChamber/main/docs/presentation/EchoChamber.pptx) | 최신 PowerPoint / LibreOffice에서 열기 |
| PPT | [PowerPoint 97–2003 호환본](docs/presentation/EchoChamber.ppt) · [다운로드](https://raw.githubusercontent.com/Min8309/echoChamber/main/docs/presentation/EchoChamber.ppt) | 구형 PowerPoint용 실제 `.ppt` 변환본 |
| 상세 설명 | [발표 구성·코드 근거·재생성 방법](docs/presentation/README.md) | 발표자 노트, 데이터 출처와 해석 범위 |

자료 구성: 문제 정의 → 사용자 흐름 → 시스템 구조 → 공식 수집 → 데이터 계약 → 토론 엔진 → SSE →
픽셀 마을 → 시각화 → AI 분석 계약 → 사용량·접근 보호 → 코드 지도 → 검증 → 데모·확장.
화면은 **합성 댓글·규칙 모드**로 촬영했습니다. 모델 성능이나 실제 여론 분석 결과를 주장하는 자료가 아닙니다.

## 실행

Python 3.12+, Node.js 22+가 필요합니다. 저장소 루트에서:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8008
```

FastAPI가 빌드된 React 화면과 API를 함께 제공합니다. 개발 시 백엔드를 먼저 켜고
`npm --prefix frontend run dev`로 Vite를 실행하세요. `/api`는 8008번 백엔드로 프록시됩니다.
React 빌드가 없는 경우 `/`는 기존 HTML 화면을 제공합니다.
기존 GitHub Pages 정적 데모(`index.html`, `stitch/`)도 그대로 유지합니다.
**새 React 버전은 FastAPI 서버가 필요하며 GitHub Pages만으로 실행되지 않습니다.**

## 작은 실험을 완주하는 흐름

1. 기존 JSON 에이전트 중 이름이 서로 다른 3명을 SQLite에 최초 한 번 복사합니다.
2. 소문 주제, 전달 단계(1~20), 모드를 선택하고 실행합니다.
3. POST `/api/runs/stream`의 SSE 이벤트로 발화를 먼저 표시하고, AI 분석이 도착하면 같은 말풍선에 병합합니다.
   현재 스트리밍 단위는 **완성된 발화 한 건**이며 토큰 단위가 아닙니다.
4. 모든 단계가 성공하면 에이전트 스냅샷·대화·관계망을 한 트랜잭션으로 저장합니다.
5. 새로고침하거나 서버를 재시작해도 히스토리에서 같은 결과를 다시 엽니다.

실행 히스토리와 실제 데이터 저장·내보내기를 지원합니다. 공개 공유 링크와 별도 시나리오 편집기는 포함하지 않습니다.

- **규칙 기반**: API 키 없이 동작. 이전 수신자가 다음 전달자가 되고, 이전 발화에 전언·추측 표현을 덧붙입니다.
  전달자와 수신자는 성향에 따른 가중치로 선택합니다. AI 생성으로 표시하지 않습니다.
- **OpenAI**: 서버의 `OPENAI_API_KEY` 또는 `ECHOCHAMBER_API_KEY`가 있을 때 선택 가능합니다.
  모델은 `OPENAI_MODEL`(기본 `gpt-4o-mini`)입니다. 단계마다 대화 생성 1회와 분석 1회, 총 2회가 발생합니다. 주제 모드는 입력 주제, 자율 모드는 선택된 에이전트의 저장된 목표에서 시작합니다.
  키는 브라우저로 보내지 않습니다. 키가 없어도 서버·조회·규칙 기반 실험은 작동합니다.
- 신뢰도는 수용 성향에 따른 감쇠값이며, 변화율은 원문과의 문자열 유사도 차이입니다.
  **사실성·의미 왜곡을 검증하는 과학적 척도가 아닙니다.** AI 모드에서도 같은 실험용 지표를 사용합니다.
- AI 요청 실패 시 오류를 표시하고 부분 실행은 저장하지 않습니다. 연결이 중단된 경우
  히스토리를 다시 불러와 완료 여부를 확인하세요. 서버가 완료한 실행은 연결 상태와 무관하게 저장될 수 있습니다.

## 데이터와 API

SQLite 기본 위치는 `data/echochamber.sqlite3`입니다. `ECHOCHAMBER_DB_PATH`로 변경할 수 있습니다.
기존 `data/*.json`은 수정하지 않습니다. 새 API의 에이전트는 최초 복사 이후 레거시 `/agents`와 별도로 유지합니다.
실행 히스토리 목록은 최근 100개를 표시하며 각 기록에는 당시 에이전트 스냅샷이 있습니다.

- `GET /api/agents`, `GET /api/capabilities`
- `POST /api/runs/stream` — `start`, `step`, `analysis`, `complete`, `error` SSE 이벤트
- `POST /api/runs` — 동일한 실행의 일반 JSON 응답
- `GET /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/network`

실행 입력: `{"topic":"마을 파티 소식", "steps":3, "engine":"rules", "seed":7}`.
`seed`는 규칙 기반 결과의 재현에 사용할 수 있으며 AI 출력의 재현성은 보장하지 않습니다.

## 검증

```bash
npm --prefix frontend run build
.venv/bin/python -m unittest discover -s tests -v
```

테스트는 임시 DB와 실제 Uvicorn HTTP 서버로 API 키 없는 시작, 입력 검증,
전파 체인, SSE 순서, 저장·재조회, AI 실패의 부분 저장 방지와 모의 AI 성공 경로를 확인합니다.
실제 OpenAI 호출은 유효한 키와 네트워크 접근이 있어야 별도 검증할 수 있습니다.

```bash
node --test tests/town.test.mjs
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python tests/browser_smoke.py
.venv/bin/python tests/browser_protection.py
```

Playwright 검증에는 시스템 Chromium(`/usr/bin/chromium`)이 필요합니다.
보호 검증의 SDK는 네트워크를 열지 않는 테스트 대역이며, 실제 FastAPI HTTP·브라우저·SQLite를 사용합니다.
브라우저 검증은 Playwright가 설치된 Python과 시스템 Chromium(`/usr/bin/chromium`)이 있는 환경에서
`.venv/bin/python tests/browser_smoke.py`로 실행합니다. 임시 DB·서버를 사용하며 실행·관계망·새로고침·히스토리·모바일·요청 실패 화면을 검증합니다.

## 호출 보호와 데모 설정

| 환경 변수 | 기본값 | 의미 |
| --- | --- | --- |
| `LLM_DAILY_UNIT_CAP` | `100` | 서버 전체의 UTC 일일 SDK 호출 시도 수. 0은 AI 호출 차단 |
| `LLM_REQUESTS_PER_HOUR` | `10` | IP별 최근 60분 AI HTTP 요청 수. 모든 AI 라우트가 공유 |
| `DEMO_READ_ONLY` | `true` | 에이전트·기억·메시지 직접 추가를 403으로 차단 |
| `DISABLE_DOCS` | `true` | `/docs`, `/redoc`, `/openapi.json` 비활성 |
| `CORS_ORIGINS` | 빈 값 | 별도 프론트엔드의 허용 Origin을 쉼표로 구분. 같은 Origin 배포는 불필요 |
| `ECHOCHAMBER_LIMITS_DB_PATH` | 실행 DB와 동일 | 쿼터를 공유·보존할 SQLite 경로 |

새 `/api/runs`·`/api/runs/stream`과 레거시 시뮬레이션·대화·반추·계획·분석 API 모두 적용됩니다.
규칙 기반 실행은 LLM 예산을 소비하지 않습니다. 읽기 전용은 **직접 추가 API**에 대한 설정이며,
실험 결과와 AI가 생성한 기억/히스토리는 계속 저장합니다. 로컬 데이터 편집·문서가 필요하면 두 플래그를 `false`로 설정하세요.

요청 시 단계 수에 필요한 최소 예산을 확인하고, 각 외부 SDK 호출 직전에 SQLite 트랜잭션으로
실제 일일 사용량을 확인·차감합니다. 재시도와 실패한 호출 시도도 카운트하며 SDK 자동 재시도는 끕니다.
동시 실행 중 남은 예산이 없어지면 스트림은 `error` 이벤트에 `status:429`와 `retry_after`를 보냅니다.
HTTP 시작 전 한도 초과는 HTTP 429와 `Retry-After` 헤더입니다. 새 `/api/runs`의 부분 실행은 저장하지 않습니다. 레거시 반복 API는 기존 단계별 저장 방식이므로 앞서 완료한 단계의 데이터가 남을 수 있습니다.
일일 단위는 **돈·토큰 한도가 아닌 호출 시도 수**이며 UTC 자정(한국 시각 오전 9시)에 새 날짜를 사용합니다.

IP는 `request.client.host`를 사용하며 임의의 `X-Forwarded-For`를 직접 신뢰하지 않습니다.
프록시 환경은 Uvicorn의 `FORWARDED_ALLOW_IPS`를 실제 신뢰하는 프록시에 맞춰 설정해야 합니다.
신뢰할 수 없는 프록시 헤더를 허용하면 IP 한도를 우회할 수 있습니다. 주소를 확인할 수 없다면 공통 IP 한도로 보수적으로 제한됩니다.
SQLite 파일이 보존되는 한 재시작 후에도 한도가 유지되지만, 서로 다른 DB를 쓰는 여러 인스턴스나
임시 파일시스템의 재배포까지 전역 한도를 보장하지는 않습니다. 운영에서는 공유/영속 저장소와 OpenAI 프로젝트 예산·알림을 별도로 설정하세요.

UI **중단**은 연결을 취소해 다음 단계 호출을 막습니다. 이미 진행 중인 호출은 과금될 수 있고,
저장 직후 연결이 끊긴 경우 히스토리에 완료 기록이 남을 수 있습니다. **재생 일시정지**는 지도 재생만 멈춥니다.
사용자가 대화를 위로 스크롤해 읽는 동안에는 새 대화가 자동으로 화면을 아래로 끌어내리지 않습니다.

기존 `/analysis/messages`의 잘못된 인자 전달을 수정했고, 수신자가 없는 댓글·리뷰도 분석할 수 있습니다.
이 배치 API도 요청 한도·행별 실제 호출 차감이 적용됩니다. 새 UI는 아래의 비공개 데이터 API를 사용합니다.

## 실제 데이터 비교 연구실

기존 마을 화면을 유지하고 좌측 **실제 데이터 비교** 메뉴를 추가했습니다.

1. 직접 댓글·리뷰를 한 줄에 한 건씩 붙여 넣거나 UTF-8 CSV를 선택합니다. 브라우저에서 최대 30행을 미리 보고 필요한 문장만 선택합니다.
2. 작성자·묶음·메시지 ID는 가명/로컬 ID로 바꾸고, 본문의 일반적인 이메일·전화번호·계정·URL을 가립니다.
   이름·주소 등 모든 개인정보를 자동 탐지하는 것은 아닙니다. 내용을 직접 수정·확인한 뒤 저장하세요.
   원본 파일·파일명·원래 작성자 ID는 서버로 전송하지 않습니다. 서버에서도 같은 연락처 가림을 다시 적용합니다.
3. 저장 즉시 기초 통계(표본 수, 평균 글자 수, 질문·전언/추측 표현 비율)를 무료로 계산합니다.
4. AI 키가 있으면 미완료 행만 AI 분석합니다. **실제 데이터 1행당 호출 1회**, 가상 대화는 단계당 생성+분석 2회입니다.
   중단·실패·한도 초과 전 완료된 행은 저장합니다. 다시 분석하면 완료 행을 건너뜁니다.
5. **이 문장으로 마을 실험**을 선택하면 익명화 텍스트와 당시 원문 분석을 마을에 연결합니다.
   실행 후 원본 데이터와 가상 대화의 그래프·수치를 같은 화면에서 비교합니다.
6. **다운로드 형식**에서 CSV·JSON·HTML을 선택합니다. 전체 행 또는 AI 완료 행만 내보낼 수 있습니다.

| 형식 | 포함 내용 |
| --- | --- |
| CSV | 익명화 문장, 행별 상태, 가십·감정·확실성·평판 영향, 모델·분석 버전. UTF-8 BOM 포함 |
| JSON | 행별 결과, 기초/AI 요약, 완료 여부·내보내기 범위, 선택한 가상 실행과의 비교 수치 |
| HTML | 설치 없이 열 수 있는 독립 보고서. 그래프·수치·행별 결과를 포함하며 외부 자원·스크립트를 사용하지 않음 |

CSV는 스프레드시트 수식으로 해석될 수 있는 문자열을 안전하게 이스케이프합니다.
HTML은 본문·모델 출력 등을 HTML 이스케이프하고 CSP로 스크립트를 차단합니다.
AI 완료 행만 선택했을 때 완료된 행이 없다면 내보내기를 차단합니다.
JSON/HTML에 포함한 비교 그래프는 저장 데이터 전체를 기준으로 하며, 내보낸 행의 범위는 별도로 명시합니다.

### 비교 기준과 개인정보

가상·실제 텍스트는 `text_analysis.py`의 같은 분석 계약을 사용합니다.
AI 수치의 직접 비교는 양쪽이 모두 분석 완료이고 모델·분석 버전이 같을 때만 제공합니다.
기초 지표는 항상 동일한 문자열 규칙을 적용하며 의미 분석·사실 확인·왜곡 측정이 아닙니다.
답글 ID가 없는 독립 댓글·리뷰에서 실제 전파 경로를 만들어 내지 않습니다.

새 데이터와 연결 실험은 **이 브라우저·도메인의 접근 키**로만 조회합니다. 키는 브라우저 저장소에,
서버에는 키 해시만 보관하며 URL·내보내기 파일에 키를 넣지 않습니다. 이는 계정 로그인 시스템이 아닙니다.
다른 브라우저·도메인이나 사이트 저장소 삭제 후에는 키 없이 복구할 수 없습니다. 브라우저 키별 저장 한도는 100개이며 삭제 후 다시 저장할 수 있습니다.
일반 데모 실행은 기존처럼 공개이며, 실제 데이터를 연결한 실행은 공개 목록·상세·관계망에서 제외합니다.
데이터 삭제 시 그 데이터에서 시작한 비공개 실험도 함께 삭제합니다.
완료된 AI 행에만 체크포인트를 쓰고 120초 작업 임대로 중복 동시 분석을 막습니다.
서버가 처리 도중 종료되면 임대 만료 후 다시 시도할 수 있습니다.
무료 Render 파일시스템의 재배포/재시작에는 데이터·한도가 초기화될 수 있으므로 중요한 결과를 내려받으세요.

새 데이터 API는 별도의 소유자 키가 필요하며 `DEMO_READ_ONLY`로 보호하는 기존 에이전트·기억·메시지 원본과 분리합니다.
키 없이 AI 행 분석은 실행할 수 없고, 기초 통계·규칙 기반 마을 실험·기초 비교·내보내기는 가능합니다.

- `POST/GET /api/datasets`, `GET/DELETE /api/datasets/{id}`
- `POST /api/datasets/{id}/analyze` — 행별 SSE·중단·이어하기. 기존 AI 한도 공유
- `GET /api/datasets/{id}/compare?run_id=...`
- `GET /api/datasets/{id}/export?format=csv|json|html&completed_only=false&run_id=...`

각 요청에는 브라우저가 생성한 `X-Dataset-Key` 헤더가 필요합니다. 실제 데이터 연결 실행은
기존 `/api/runs`·`/api/runs/stream`에 `dataset_id`, `dataset_row_id`와 같은 헤더를 전달합니다.

추가 검증:

```bash
node --test tests/csv.test.mjs tests/town.test.mjs
.venv/bin/python tests/browser_research.py
```

## 배포

Dockerfile은 React를 빌드한 다음 FastAPI와 함께 제공합니다. `render.yaml`도 같은 Docker 배포를 사용합니다.
공개 운영 전에는 인증·호출 제한을 추가해야 합니다. 공개 방문자는 한도 안에서 비용이 발생하는 AI 실행을 요청할 수 있으므로 인증이 필요한 운영에는 별도 접근 제어를 추가하세요.
SQLite 히스토리를 재배포 후에도 유지하려면 **영속 볼륨**을 연결하고 `ECHOCHAMBER_DB_PATH`를 해당 경로로 설정해야 합니다.
Render 무료 플랜의 임시 파일시스템만으로는 영속성을 보장할 수 없습니다.

---

## 기존 프로젝트 소개

프로젝트 구현 목적

- 🌐 **온라인 데모 (GitHub Pages)**: [[https://min8309.github.io/echoChamber/](https://min8309.github.io/echoChamber/)](https://min8309.github.io/echoChamber/)
- 💻 로컬 서버 접속: http://localhost:8008


[echochamber.pptx](https://github.com/user-attachments/files/32836162/echochamber.pptx)


소문의 시작점을 찾고, 전달 과정에서 달라지는 사실과 신뢰도의 변화를 수치로 추적합니다.


EchoChamber는 대화 속에서 소문이 처음 시작된 지점을 추적하고, 사람과 사람 사이로 전달되는 과정에서 내용이 어떻게 변형되는지를 분석하는 AI 기반 플랫폼입니다. 소문의 전달 경로와 함께 의미 왜곡 정도, 정보 신뢰도 변화, 감정 방향, 평판 영향을 수치와 네트워크로 시각화하여 소문의 생성과 확산 과정을 직관적으로 확인할 수 있도록 구현했습니다.

핵심 기능 표현
- 최초 발화와 소문의 시작점 추적
- 전달자와 수신자 간 확산 경로 시각화
- 원래 내용과 전달된 내용의 의미 차이 측정
- 전달 단계별 정보 신뢰도 변화 분석
- 감정과 평판 영향의 누적 변화 확인
- 실제 댓글과 가상 에이전트 대화 비교 분석


<img width="1031" height="626" alt="image" src="https://github.com/user-attachments/assets/7b5a47d4-9352-414c-a28f-8728e8cde58a" />

<img width="1260" height="821" alt="image" src="https://github.com/user-attachments/assets/955d9cd7-bc07-4772-b789-1091082da555" />
<img width="1252" height="730" alt="image" src="https://github.com/user-attachments/assets/14e87510-8ed4-422a-8581-14687577d201" />


## 공식 댓글 수집 · 연구 데이터 가져오기

좌측 **실제 데이터 비교 → 공식 API · 공개 연구 댓글 가져오기**에서 수집한 뒤,
익명화 미리보기와 확인을 거쳐 저장합니다. 기존 AI 분석·마을 연결·CSV/JSON/HTML 다운로드를 그대로 사용합니다.

- **YouTube**: Render Environment에 `YOUTUBE_API_KEY`를 추가합니다. Google Cloud에서 YouTube Data API v3를 활성화하고 키의 API 사용 범위를 제한하세요. 영상 주소/ID로 `commentThreads.list`와 `comments.list`를 호출하며 답글의 부모 관계를 유지합니다. 키를 브라우저나 GitHub에 넣지 않습니다. 키 미설정·댓글 차단·할당량 초과는 오류로 안내합니다.
- **K-HATERS**: [공식 저장소](https://github.com/ssu-humane/K-HATERS)가 안내하는 `humane-lab/K-HATERS`의 Hugging Face 데이터 뷰어에서 최대 30건을 가져옵니다. CC BY 4.0 출처·저자 표시와 변경 내용을 다운로드에도 포함합니다. Park et al., 2023, *K-HATERS: A Hate Speech Detection Corpus in Korean with Target-Specific Ratings*.
- **KOLD**: [공식 저장소](https://github.com/boychaboy/KOLD)의 JSON 파일을 사용자가 이용 조건을 확인한 후 선택합니다. 명시적인 재배포 라이선스를 확인하지 못해 서버 자동 수집은 제공하지 않습니다. Jeong et al., 2022, *KOLD: A Large-scale Korean Offensive Language Dataset*. 원 저장소의 악의적인 생성·게시용 학습 제한도 확인하세요.

연구 JSON/JSONL은 파일 전체를 업로드하지 않고 브라우저에서 첫 30건만 읽습니다.
공격성·표적 참고 라벨은 AI가 계산한 가십 지표와 구분하며, 원본 주석자 ID는 보내지 않습니다.
공식 API라는 사실이 모든 재사용을 허용하는 것은 아닙니다. YouTube API 이용약관·개발자 정책과 댓글 이용 권한을 확인하세요.
YouTube 수집 데이터는 29일 만료로 저장하며 만료 시 연결 실험까지 제거합니다(요청 시 및 매시간 정리).
다운로드한 사본은 사용자가 관리합니다.

`COLLECTION_REQUESTS_PER_HOUR`(기본 10)는 IP당 수집 요청 제한,
`COLLECTION_DAILY_CALL_CAP`(기본 200)은 서버 전체 외부 HTTP 시도 제한입니다.
수집당 HTTP 시도는 최대 10회이며 LLM 호출 한도와 별도로 관리합니다.
외부 통신이 제한된 서버는 `www.googleapis.com`, `datasets-server.huggingface.co`를 허용해야 합니다.
실제 Google API 호출은 서버 키가 있어야 검증할 수 있습니다.

### 실제 데이터 중심 시작 화면

첫 접속은 실제 데이터 비교 연구실로 열립니다. 왼쪽 메뉴의 실제 데이터를 맨 위로 배치하고,
가져오기 → 익명화·분석 → 가상 마을 전달 → 그래프 비교·다운로드 흐름을 표시합니다.
저장한 문장에서 마을 실험을 실행한 뒤 ‘실제 데이터 · 결과 비교로 돌아가기’를 누르면
현재 연결 실험이 비교 대상으로 자동 선택됩니다. 기존 대시보드·마을·실행 기록도 메뉴로 이동할 수 있습니다.

### 자료 묶음으로 3~4인 토론

실제 데이터 저장 후 **정보 정렬**(수집 순서/문장 길이/AI 부정 감정/별점)과 검색으로
목록을 정리하고, 체크박스로 최대 10건을 선택하세요. **마을 토론 준비**에서 3명 또는
4명을 선택할 수 있습니다. 4명은 기존 3인에 실행 전용 가상 자료 검토자가 합류하며
저장된 기본 에이전트를 변경하지 않습니다.

선택 자료·분석·출처를 비공개 실행에 스냅샷으로 저장합니다. OpenAI 모드는 전체 선택 자료와
최근 4개 발언을 함께 제공하고, 인물이 차례로 자료 요약/근거 점검/다른 관점/종합 정리를
수행합니다. 단계마다 생성 1회와 의미 분석 1회를 사용합니다. 단계 수는 참여 인원과 자료 수
이상이어야 하며 최대 20회입니다. 규칙 모드는 별도 표시된 검토 문장 템플릿으로 동선을
실험하는 기능이며 AI 토론·의미 분석을 대신하지 않습니다.

마을 화면에서 자료별 배정 순서, 인물별 발언 횟수, AI 감정 분포, 단계별 전달 지표와
선택한 실제 자료 대비 기초/AI 비교를 표시합니다. 자료 배정은 모델의 근거 인용 정확도를
검증한 결과가 아닙니다. 성향 기반 신뢰도와 첫 자료 대비 문자열 변화율은 사실성·정보 정확도
점수가 아니며, 자료 간 주제 차이도 포함합니다. 기존 단일 문장 전달 실험도 유지합니다.
