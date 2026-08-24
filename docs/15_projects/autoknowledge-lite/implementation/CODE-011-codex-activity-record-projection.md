# CODE-011 Codex Activity Record Projection

- 작성일: 2026-08-18
- 상태: Complete

## 구현 목표

기존 `codex/development_session` Capture의 `commands`, `changedFiles`, `tests`를
수정하지 않고 공통 지식 모델의 `Activity`, `CommandRecord`, `FileRecord`,
`TestRecord`로 읽기 전용 투영한다.

## 구현 내용

- 기존 Viewer와 동일한 `task:{captureId}:session` ID로 레코드를 귀속한다.
- 원본 실행·파일·테스트 레코드는 `provenance.source=original`로 기록한다.
- 원본 레코드와 공통 객체를 연결하는 Activity는
  `provenance.source=derived`, `derivedBy=rule`로 구분한다.
- 원본 `commandId`와 `testId`가 있으면 재사용하고, 없으면 안정적인 투영 ID를
  생성한다.
- Test의 `commandId`가 기존 Command를 가리키면 명령, 시간, exit code와 출력을
  읽기 전용으로 연결한다.
- 지원하지 않거나 불완전한 개별 레코드는 원본 저장을 실패시키지 않고 warning을
  남긴 뒤 해당 레코드만 투영에서 제외한다.
- Capture Envelope, Session Markdown, 기존 저장 포맷은 변경하지 않는다.

## 검증 범위

- Command, changed file, Test와 대응 Activity 생성
- 원본 ID 재사용과 누락 ID 합성
- renamed 파일의 이전 경로 보존
- 부분 손상 레코드 격리와 warning
- 입력 Capture payload 불변성
