# TEST-033 Step 10 전체 회귀 및 모바일 검증

## 일자

2026-08-20

## 자동화 테스트

- AutoKnowledge-Lite Python: 216 passed, 1 skipped
- MDE Knowledge: 68 passed
- Knowledge Viewer: 42 passed
- AutoKnowledge-Lite Android JVM: 24 passed, failures 0, errors 0
- Knowledge Viewer Android JVM: 3 passed, failures 0, errors 0
- Knowledge Viewer TypeScript production build: passed

Android JVM 테스트는 `--rerun-tasks`로 현재 작업에서 실제 재실행했다.

## APK 검증

### AutoKnowledge-Lite

- 파일: `apps/autoknowledge-lite/android/app/build/outputs/apk/debug/app-debug.apk`
- 크기: 101,765 bytes
- SHA-256: `B5235A81639C692344F7CCD4705F7BD5E7ECC1FAA26E514AA46796A557F875B7`
- APK Signature Scheme v2: verified
- 다운로드 파일명: `autoknowledge-lite-v0.2.4.apk`

### MDE Knowledge Viewer

- 파일: `apps/knowledge-viewer/android/app/build/outputs/apk/debug/app-debug.apk`
- 크기: 13,023 bytes
- SHA-256: `E3045F8BC0B9FE6D3C71AF06B561290C6B70FBC9BCBDC5E7830748459C37946D`
- APK Signature Scheme v2: verified
- 다운로드 파일명: `mde-knowledge-viewer-v0.1.0.apk`

localhost와 Tailscale `100.75.235.67`의 8000/8765 다운로드 파일은 각각 로컬 APK와 SHA-256이 일치했다.

## 실제 저장 데이터 읽기 검증

- Knowledge Source: 2개
- Markdown Document: 224개
- Codex development Session: 1개
- ChatGPT Session: 2개
- ChatGPT Message: 23개
- ChatGPT Task: 2개
- ChatGPT Activity: 21개
- 통합 Graph: node 81개, edge 128개
- ChatGPT Timeline: 48개

Graph에는 `DOCUMENT`, `PROJECT`, `DEVELOPMENT_SESSION`, `CHATGPT_SESSION`, `CHATGPT_MESSAGE`, `TASK`, `ACTIVITY`, `FILE` 노드가 실제로 조회됐다.

현재 저장소에는 독립 general, ChatGPT, Codex clipboard Clip 레코드가 없어서 각 목록은 0건이었지만 API는 HTTP 200으로 정상 응답했고 기존 Clip 호환성은 전체 Python·Viewer 회귀 테스트로 확인했다.

## 서비스 상태

- `MDE-AutoKnowledge-Lite`: Running
- `MDE-Knowledge-Viewer`: Running
- AutoKnowledge API `:8000`: HTTP 200
- Knowledge Viewer `:8765`: HTTP 200
