# CODE-027 ChatGPT 실제 세션 Viewer 통합

- 작성일: 2026-08-19
- 상태: Complete

## 목적

ChatGPT Data Export 및 공개 Shared Link에서 보존한 읽기 전용 투영을 MDE Knowledge Viewer에서 조회한다. 기존 Markdown, ChatGPT Clip, 원본 snapshot 및 projection revision 형식은 변경하지 않는다.

## 구현

- AutoKnowledge-Lite에 ChatGPT Session 목록·검색·상세·Message 조회 API 추가
- 최신 immutable projection revision만 읽는 query service 추가
- 응답 provenance에 `source=original`, derived 여부 및 confidence를 명시
- import ID, 원본 파일 경로 및 content hash는 조회 응답에서 제외
- MDE Knowledge 8765 서버에 `/api/v1/chatgpt/*` gateway 추가
- Viewer ChatGPT 탭을 실제 세션 목록, 검색, 메시지 상세, 가져오기 화면으로 확장
- 많은 세션과 메시지는 cursor pagination을 끝까지 조회
- Knowledge Graph에 `CHATGPT_SESSION`, `CHATGPT_MESSAGE`, `contains_message` 관계 추가
- 기존 Capture Graph 컴포넌트를 재사용하고 기존 문서·Capture 화면은 유지

## 운영 확인

8765 gateway에서 보존된 실제 Session 1개와 Message 9개를 조회했다. 동일 세션의 graph 응답은 Session node 1개, Message node 9개, edge 9개이며 Tailscale Viewer 주소도 HTTP 200을 반환했다.

