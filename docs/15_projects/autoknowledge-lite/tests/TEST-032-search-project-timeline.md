# TEST-032 관계 검색 및 Project Timeline

## 일자

2026-08-20

## 추가 검증

- Message, Task, Activity 검색과 Session/Task/Message 관계 컨텍스트
- 원본과 derived provenance 구분
- timestamp가 없는 항목을 생성하지 않는 Timeline
- ChatGPT와 Codex Capture 이벤트의 시간순 병합
- Timeline에서 원본 ChatGPT 및 Capture 화면 이동
- 기존 Session, Task, Graph, Import 화면 회귀

## 결과

- ChatGPT Query 집중 테스트: 8 passed
- Viewer 집중 테스트: 19 passed
- Viewer 전체 회귀: 42 passed
- AutoKnowledge-Lite 전체 회귀: 216 passed, 1 skipped
- MDE Knowledge 전체 회귀: 68 passed
- Ruff: passed
- Black `--fast --check`: passed
- TypeScript production build: passed

## 실행 검증

- 로컬 API와 Viewer 서비스를 재시작한 후 `/api/v1/chatgpt/search`: HTTP 200
- `/api/v1/chatgpt/timeline`: HTTP 200
- 실제 저장 데이터 검색 결과: 1건
- 실제 Timeline: 48건, timestamp 누락 0건
- Viewer: HTTP 200 및 최신 production bundle 제공 확인

Control API Key는 테스트 프로세스에서만 비워 mutation API 테스트가 로컬 실행 환경의 인증 설정에 영향받지 않도록 했다.
