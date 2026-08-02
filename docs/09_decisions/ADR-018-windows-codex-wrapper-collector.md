# ADR-018 Windows Codex 래퍼 수집기

- 상태: Accepted
- 결정일: 2026-08-02

## 배경

Codex 내부 세션 형식은 이번 단계의 안정적인 계약이 아니다. 개발 세션을 재현 가능한 근거로 남기려면 실제 Git 상태와 MDE가 직접 실행한 명령 결과를 수집해야 한다.

## 결정

- `mde codex start`와 `finalize` 사이의 Git 스냅샷을 비교한다.
- 기본 실행 방식은 수동 시작·종료이다.
- PATH에서 Codex 실행 파일이 탐지된 경우에만 `start --launch`를 제공한다.
- Codex 내부 세션 및 대화 파일은 읽지 않는다.
- 시작 전 dirty 변경은 `PRE_EXISTING`, 추가 변화의 귀속이 불명확하면 `UNKNOWN_ATTRIBUTION/low`로 기록한다.
- 민감 파일은 patch에서 제외하며 텍스트는 저장 전에 마스킹한다.
- API 장애는 로컬 queue, 서버 민감정보 거부는 quarantine으로 분리한다.

## 결과

수집 결과는 Capture Envelope 1.0의 `development_session`으로 전송한다. 전체 대화 연결은 통합 개발 4단계에서 별도 어댑터로 처리한다.
