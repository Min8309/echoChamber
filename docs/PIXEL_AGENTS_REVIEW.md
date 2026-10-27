# Pixel Agents 첨부 코드 검토

ZIP SHA-256: `3e0a9bc24b8ea57d0e9792d50e98adcc5cb953b60cd90dd4b011b9280ee1bf68`.

검토 대상: 사용자가 첨부한 `pixel-agents-main (1).zip`, 패키지 버전 1.5.0.
첨부 문서는 분석 자료로 취급했으며 프로젝트 작업 지시로 적용하지 않았습니다.
설치 스크립트·Claude 훅·터미널 코드는 실행하지 않았습니다.

## 결론

**시각화 부분은 재사용 후보이나, 전체 앱을 합치는 것은 권장하지 않습니다.**
EchoChamber는 FastAPI가 소문 전달을 실행하고 SSE로 대화를 보내는 실험 도구입니다.
Pixel Agents는 실제 Claude Code 작업·터미널 상태를 픽셀 사무실에 표시하는 도구입니다.
시각 엔진과 실험 엔진을 구분하면 기존 API와 저장 기능을 유지할 수 있습니다.

| 첨부 파일의 코드 | 현재 프로젝트 적합성 | 적용 방법 |
| --- | --- | --- |
| `webview-ui/src/office/engine/gameLoop.ts` | 높음 | requestAnimationFrame 루프·프레임 시간 상한·루프 정리 구조를 향후 마을 애니메이션에 사용 |
| `webview-ui/src/office/engine/renderer.ts` | 조건부 | Canvas 2D 렌더링·깊이 정렬 등의 구조를 마을 배경과 캐릭터용으로 분리. 사무실 데이터 모델 의존성은 제거 필요 |
| `webview-ui/src/office/engine/characters.ts` | 조건부 | IDLE/WALK/TYPE 상태 중 TYPE을 말하기 상태로 바꾸고, 실제 SSE 이벤트의 발화자·청자에 연결 |
| `webview-ui/src/office/layout/tileMap.ts` | 높음 | 4방향 BFS와 이동 가능 타일 처리는 카페·도서관 사이 이동에 활용 가능. 배경 이미지와 별도로 충돌·경로 타일맵이 필요 |
| `webview-ui/src/office/components/OfficeCanvas.tsx` | 조건부 | 확대·이동·선택 UI 참고. officeState, 에디터, transport 등 의존성을 분리한 VillageCanvas가 필요 |
| `webview-ui/public/assets/characters/char_0.png`~`char_5.png` | 향후 후보 | 스프라이트 규격·저작권 고지를 확인해 별도 로컬 자산으로 관리. 이번 변경에는 복사하지 않음 |
| `core/src/messages.ts`, `schemas.ts` | 구조 참고 | ID·이벤트 타입을 명시하는 방식은 유용. 현재 start/step/complete/error SSE 계약을 대체할 필요는 없음 |
| `server/src/providers/`, transcriptParser, fileWatcher, terminal | 도입 불필요 | Claude 세션 파일 감시·CLI·터미널 실행 기능은 마을 소문 실험과 역할이 다름 |
| `adapters/vscode/` | 도입 불필요 | 웹 기반 React + FastAPI에는 VS Code 확장 호스트가 없음 |
| 레이아웃 에디터·가구·반려동물·멀티 서버 기능 | 현재 범위 밖 | 3명·대화·관계망·히스토리 완성 후 필요할 때 검토 |

## 라이선스와 의존성

루트 `LICENSE`는 **MIT, Copyright (c) 2026 Pablo De Lucca**입니다.
코드나 상당 부분을 가져오면 저작권 문구와 MIT 전문을 함께 보존해야 합니다.
별도 라이선스·크레딧 파일은 ZIP 파일명 검색에서 확인되지 않았지만,
이는 모든 이미지의 별도 권리관계를 보증하지 않습니다.
`docs/external-assets.md`에 언급된 외부 타일셋은 별도 자산이므로 MIT 코드와 같은 권리로 가정하면 안 됩니다.

현재 EchoChamber와 첨부 앱은 모두 React 19 계열입니다. 다만 첨부 UI는 TypeScript와 Vite 8,
현재 UI는 JavaScript와 Vite 7을 사용하므로 설정·의존성을 통째로 복사하지 않는 편이 좋습니다.
첨부 앱의 Fastify·WebSocket·xterm·node-pty는 현재 FastAPI·SSE 흐름에 필요하지 않습니다.

## 이번에 실제 반영한 것

1. 저장소의 `stitch/screen.png`를 변경 없이 `frontend/public/assets/smallville-reference.png`로 복사했습니다.
2. React `VillageScene`의 SVG viewport로 기존 디자인 이미지 중 마을 영역만 표시합니다.
   외부 Google 이미지 서버에 의존하지 않으며, 이는 새 애니메이션 엔진이 아닌 **컨셉 장면 복원**입니다.
3. 마을 + 실제 대화 패널을 나란히 배치하고 실제 관계망은 그 아래에 유지했습니다.
4. 현재 실험의 에이전트·마지막 발화·전달자/수신자는 API 기록에서 표시합니다.
   배경 이미지 속 인물과 말풍선은 실제 실험 데이터가 아님을 화면에 명시합니다.
5. Pixel Agents 코드·자산은 이번 구현에 가져오지 않았습니다. 라이선스 고지를 누락한 복사를 하지 않았습니다.

## 다음 단계 제안

필요하다면 `VillageCanvas` 하나만 추가해 3명의 픽셀 캐릭터와 말풍선을 현재 SSE에 연결합니다.
이때 마을 이동 타일맵과 캐릭터 상태 모델을 만들고, 첨부 코드의 경로 탐색·프레임 루프만 분리 이식합니다.
실험의 DB·FastAPI·관계망은 유지합니다. 이번 요청 범위에서는 이 확장 작업을 실행하지 않았습니다.
