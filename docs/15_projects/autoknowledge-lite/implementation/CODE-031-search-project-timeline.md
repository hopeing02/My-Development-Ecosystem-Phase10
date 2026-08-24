# CODE-031 관계 검색 및 Project Timeline

## 구현 범위

- ChatGPT Session, Message, Task, Activity 관계 검색 API
- 실제 timestamp 기반 ChatGPT Timeline API
- ChatGPT 화면의 관계 검색 결과와 원본 Session/Task/Message 이동
- ChatGPT Timeline과 Codex·일반 Capture의 `capturedAt`을 결합한 최상위 Project Timeline
- Timeline 항목에서 기존 ChatGPT 또는 Capture Viewer로 이동

## 호환성

- 기존 문서 검색 API와 UI는 변경하지 않았다.
- 기존 Capture 검색·필터와 상세 화면은 변경하지 않았다.
- 기존 ChatGPT Session 검색은 유지하며 구조화 검색 결과를 함께 표시한다.
- 기존 Markdown, Clip, Session 원본 및 projection revision을 수정하지 않는다.
- 한 데이터 소스 조회가 실패해도 다른 Timeline 데이터는 표시하고 warning으로 격리한다.

## 주요 파일

- `apps/autoknowledge-lite/src/autoknowledge_lite/chatgpt_query.py`
- `apps/knowledge-viewer/src/features/chatgpt-import/ChatGPTImportPanel.tsx`
- `apps/knowledge-viewer/src/features/timeline/TimelineWorkspace.tsx`
- `apps/knowledge-viewer/src/App.tsx`
- `apps/knowledge-viewer/src/styles.css`

## 결과

사용자는 ChatGPT Task/Activity 검색 결과에서 관련 Session과 원본 Message로 이동할 수 있고, Project Timeline에서 ChatGPT 설계 흐름과 Codex/Capture 작업을 시간순으로 함께 볼 수 있다.
