# EchoChamber · React + FastAPI 실험 도구

기존 파란색·흰색 대시보드 디자인을 유지한 최소 기능 버전입니다.
**에이전트 3명 → 단계별 대화 스트리밍 → 방향성 관계망 → 실행 히스토리**에 집중합니다.

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
3. POST `/api/runs/stream`의 SSE 이벤트로 각 발화가 끝날 때마다 대화와 관계망을 갱신합니다.
   현재 스트리밍 단위는 **완성된 발화 한 건**이며 토큰 단위가 아닙니다.
4. 모든 단계가 성공하면 에이전트 스냅샷·대화·관계망을 한 트랜잭션으로 저장합니다.
5. 새로고침하거나 서버를 재시작해도 히스토리에서 같은 결과를 다시 엽니다.

콘텐츠 기능은 **실행 히스토리 하나**로 한정했습니다. 시나리오 편집·공유 링크·다중 그래프는 포함하지 않습니다.

- **규칙 기반**: API 키 없이 동작. 이전 수신자가 다음 전달자가 되고, 이전 발화에 전언·추측 표현을 덧붙입니다.
  전달자와 수신자는 성향에 따른 가중치로 선택합니다. AI 생성으로 표시하지 않습니다.
- **OpenAI**: 서버의 `OPENAI_API_KEY` 또는 `ECHOCHAMBER_API_KEY`가 있을 때 선택 가능합니다.
  모델은 `OPENAI_MODEL`(기본 `gpt-4o-mini`)입니다. 단계마다 API 호출 1회가 발생합니다.
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
- `POST /api/runs/stream` — `start`, `step`, `complete`, `error` SSE 이벤트
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
브라우저 검증은 Playwright가 설치된 Python과 시스템 Chromium(`/usr/bin/chromium`)이 있는 환경에서
`python3 tests/browser_smoke.py`로 실행합니다. 임시 DB·서버를 사용하며 실행·관계망·새로고침·히스토리·모바일·요청 실패 화면을 검증합니다.

## 배포

Dockerfile은 React를 빌드한 다음 FastAPI와 함께 제공합니다. `render.yaml`도 같은 Docker 배포를 사용합니다.
공개 운영 전에는 인증·호출 제한을 추가해야 합니다. 현재는 신뢰할 수 있는 사용자용 단일 서버 프로토타입이며,
공개 API에 서버 키를 연결하면 방문자가 비용이 발생하는 AI 실행을 요청할 수 있습니다.
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
