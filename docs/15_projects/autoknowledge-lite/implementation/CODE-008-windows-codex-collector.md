# CODE-008 Windows Codex 작업 수집기

## 구현

- `mde.codex_capture.git`: Git 저장소 탐지, 스냅샷, 변경 귀속, 안전한 patch 생성
- `mde.codex_capture.security`: Windows 경로 별칭과 민감정보 마스킹
- `mde.codex_capture.service`: 등록, 세션, 명령, artifact, queue/retry, API 전송
- `mde.codex_capture.cli`: `mde codex` 명령 표면
- `PersistingDevelopmentSessionHandler`: 검증, 멱등성, revision, Markdown 및 첨부 저장

수집기는 Codex 대화 파일을 읽지 않는다. 변경 귀속은 Git 스냅샷만 사용한다.
