# SDS-007 Android Codex 발췌와 Windows 세션 연결

- 버전: 1.0
- 상태: Implemented

## 구성

```text
Capture 저장
  -> capture-match-index-v1.json
  -> CaptureRelationMatcher
  -> capture-relations-v1.json
  -> 관계 조회·승인·거절·해제 API

Android Codex 화면
  -> 인증된 Mobile Control API
  -> Windows CodexCaptureService
  -> 공식 Codex App Server thread/list, thread/read
```

## 연결 계약

from은 `codex/clipboard_item/android`, to는 `codex/development_session/windows`만 허용한다. 정확 메시지 해시는 100점, 포함 일치는 비율에 따라 60 또는 80점, 연속 메시지는 70점이다. 같은 프로젝트 20점, 시간 근접 8~20점, 같은 Codex client 계열 5점을 더한다. 100점 이상인 유일 후보는 확정하고 75~99점 또는 최고점 동점은 제안한다.

명시적 프로젝트 불일치와 24시간 초과 후보는 제외한다. 포함 일치는 100자 이상, 비율 80% 이상, 최대 20개 후보 세션에만 적용한다. 근거에는 본문을 넣지 않고 해시, 메시지 ID, 비율, 시간 차이, 프로젝트 일치와 대상 revision만 저장한다.

## Revision과 실패

관계 대상은 안정적인 `captureSessionId`다. 새 revision에서 근거가 사라지면 확정 관계를 삭제하지 않고 `stale`로 바꾼다. 관계 작업 오류는 `capture-relation-jobs-v1.json`에 Capture ID, 오류 코드와 재시도 횟수만 남기고 원 Capture 저장 성공을 유지한다.

## 기존 자료

Backfill은 기존 Capture 인덱스의 Android Markdown 원문과 Windows 수집기 `envelope.json`을 읽어 matching 인덱스를 보강한다. dry-run은 임시 인덱스에서 수행해 관계·문서·운영 인덱스를 변경하지 않는다.
