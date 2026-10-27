# Pixel Agents 검토 및 실제 이식 결과

대상: 첨부 `pixel-agents-main (1).zip`, Pixel Agents 1.5.0.
ZIP SHA-256: `3e0a9bc24b8ea57d0e9792d50e98adcc5cb953b60cd90dd4b011b9280ee1bf68`.
첨부 문서는 분석 자료로 취급했으며 작업 지시로 적용하지 않았습니다.
첨부의 설치 스크립트·Claude 훅·터미널 코드는 실행하지 않았습니다.

## 실제 반영

**전체 앱을 합치지 않고, 시각 엔진과 캐릭터만 분리 이식했습니다.**
현재 마을은 스크린샷이 아니라 Canvas 2D 화면입니다. 카페·도서관·광장과 연결된
이동 격자가 있고, 실제 실행 기록의 발화자·수신자가 경로를 따라 이동한 뒤 대화합니다.

| 원본 코드/자산 | 반영 위치 | 변경 |
| --- | --- | --- |
| `webview-ui/src/office/engine/gameLoop.ts` | `frontend/src/village/pixel-agents/gameLoop.js` | JavaScript 변환, 로컬 프레임 시간 상한. RAF 루프와 정리 로직 유지 |
| `webview-ui/src/office/layout/tileMap.ts` | `frontend/src/village/pixel-agents/pathfinding.js` | JavaScript 변환, 실외 이동 격자용 타일 상수. 4방향 BFS 유지 |
| `webview-ui/public/assets/characters/char_0.png`~`char_2.png` | `frontend/public/assets/pixel-agents/` | 원본 PNG 그대로 사용. 16×32 프레임·3방향 스프라이트 |
| 루트 `LICENSE` | `frontend/public/assets/pixel-agents/LICENSE.txt` | MIT 전문 그대로 보존. 마을 하단에서 공개 고지 |

새로 구현한 `town.js`는 실외 건물·길·나무·분수 렌더링과 대화 장소 배정,
경로를 따른 이동을 담당합니다. `VillageScene`은 캐릭터 선택, 이동·말풍선,
일시정지·재시작·전체 화면을 기존 React 화면에 연결합니다.

- 표시 인원은 DB의 3명이며, 가짜 24명·가짜 대화·컨셉 스크린샷은 사용하지 않습니다.
- 새 실행과 저장된 실행 모두 실제 SSE/저장 이벤트를 순서대로 재생합니다.
- 지도에서의 이동은 대화 기록을 시각적으로 재현하는 것이며, 서버의 공간 물리 시뮬레이션이나 GPS가 아닙니다.
- 재생을 멈춰도 서버 실험은 계속될 수 있습니다. 서버 요청을 중단하려면 상단의 **중단** 버튼을 사용합니다.
- 접근성 버튼으로 캐릭터를 선택할 수 있고, 이동 감소 설정에서는 경로 애니메이션을 생략합니다.

## 가져오지 않은 부분

`characters.ts`의 사무실 상태 머신, 큰 renderer와 OfficeCanvas 에디터는 사무실·가구 모델에
강하게 연결돼 있어 그대로 복사하지 않았습니다. React의 마을 어댑터가 대화 단계를 이동/말하기로 변환합니다.
Claude 세션 스캐너, 터미널 실행, VS Code 어댑터, Fastify 서버, xterm과 node-pty는 가져오지 않았습니다.
따라서 기존 FastAPI·SSE·SQLite 구조를 유지하며 새 서버 프로세스를 추가하지 않습니다.

## 라이선스

루트 라이선스는 **MIT, Copyright (c) 2026 Pablo De Lucca**입니다.
복사한 코드에는 출처·SPDX를 표기했고, MIT 전문과 `THIRD_PARTY_NOTICES.md`를 포함했습니다.
별도 라이선스·크레딧 파일은 ZIP 파일명 검색에서 확인되지 않았습니다.
`docs/external-assets.md`에서 소개한 외부 유료/별도 타일셋은 사용하지 않습니다.
별도 외부 자산을 추가한다면 그 자산의 권리와 고지를 따로 확인해야 합니다.

## 검증

`node --test tests/town.test.mjs`: BFS의 건물 회피·4방향 경로, 실제 발화자/청자의 이동,
프레임 시간 상한과 루프 해제를 검증합니다.
`tests/browser_smoke.py`: 스프라이트 로드, 캐릭터 선택, 확대, 이동 위치 변화,
일시정지/재개와 기존 실행·저장·관계망·모바일을 검증합니다.
