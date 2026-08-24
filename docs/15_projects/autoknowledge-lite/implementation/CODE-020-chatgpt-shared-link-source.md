# CODE-020 ChatGPT Shared Link Source

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

사용자가 명시적으로 확보한 ChatGPT Shared Link HTML snapshot에서 실제로 포함된
구조화 conversation 1건만 공통 ChatGPT Adapter 입력으로 읽기 전용 제공한다.

## 범위

- 공식 `https://chatgpt.com/share/<conversation-ID>` URL만 허용
- credential, query, fragment, 비표준 port와 유사 도메인 거부
- local UTF-8 snapshot을 수정하거나 추출하지 않고 크기 제한 안에서 판독
- JSON 및 JSON string으로 포함된 conversation payload 탐색
- 같은 payload는 content hash로 중복 제거
- 여러 conversation이 있으면 URL ID 일치 후보를 우선하고 warning 기록
- session ID, title, timestamp, message 등 누락 값을 생성하지 않음
- 기존 `ChatGPTKnowledgeAdapter`가 원본 provenance로 Session/Message 투영

## 비범위

이 Source는 ChatGPT 계정, sidebar 또는 최근 세션 목록에 접근하지 않는다. 네트워크
fetch와 raw snapshot 보존은 별도 명시적 단계로 분리한다. Shared Link는 계정 전체
export를 대체하지 않으며 한 시점의 공개 conversation snapshot이다.

## 기존 기능 호환

기존 URL-only ChatGPT Clip 판독이 현재 `/share/` 경로도 인식하도록 확장했다. 기존
`/s/` 지원, 일반 URL Clip, Markdown, Codex와 Export ZIP 처리 방식은 유지한다.
