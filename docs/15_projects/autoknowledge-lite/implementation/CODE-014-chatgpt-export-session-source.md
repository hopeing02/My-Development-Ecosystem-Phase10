# CODE-014 ChatGPT Export Session Source

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

사용자가 명시적으로 선택한 ChatGPT Data Export ZIP에서 실제 Session을 로컬·읽기
전용으로 발견한다. 이 단계에서는 원본 Archive 저장, Adapter 투영, API와 Viewer
연결을 수행하지 않는다.

## 구현

- 기존 `CodexSessionSource`와 같은 discover/read/supports 책임 분리
- `ChatGPTSessionSource` Protocol과 `ChatGPTExportSource` 구현
- `conversations.json`, `conversations-N.json`, `conversations_N.json` 지원
- 실제 Session ID, 제목, 원본 ZIP member와 배열 index를 reference로 보존
- Session ID와 ZIP SHA-256으로 원본 식별 기반 제공
- 분할 JSON 사이의 중복 Session ID 제거 및 warning 기록
- 손상 JSON, 비객체 record와 ID 없는 Session을 warning으로 격리
- ZIP을 파일시스템에 해제하지 않고 필요한 JSON만 메모리에서 읽음

## 보안 경계

- 파일 크기, member 수, JSON 크기와 전체 압축 해제 크기 제한
- 절대 경로, drive 경로와 `..` 경로를 포함한 ZIP member 거부
- 암호화 member와 중복 member 경로 거부
- conversations JSON이 없는 Archive와 잘못된 ZIP을 명시적 오류로 구분
- 입력 ZIP을 수정하거나 삭제하지 않음

## 호환성

기존 ChatGPT Clip, Markdown, Capture API, Codex 수집, Knowledge Graph와 Viewer는
수정하지 않았다.
