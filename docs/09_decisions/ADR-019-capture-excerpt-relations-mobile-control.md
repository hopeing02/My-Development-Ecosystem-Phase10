# ADR-019 Capture 발췌 관계와 모바일 Codex 제어 API

- 상태: Accepted
- 결정일: 2026-08-03

## 배경

Android의 Codex 클립보드 단편과 Windows의 전체 공개 개발 세션은 목적이 다른 원본이다. 본문 중복 제거로 합치면 모바일 발췌 시점과 전체 개발 근거 중 하나를 잃는다. 또한 Android가 Codex App Server나 로컬 세션 파일에 직접 접근하면 인증되지 않은 원격 인터페이스와 개인 경로가 노출된다.

## 결정

- 두 Capture를 보존하고 Android `clipboard_item`에서 Windows `development_session`으로 향하는 `excerpt_of` 관계만 저장한다.
- 관계 상태는 `suggested`, `confirmed`, `rejected`, `stale`, `removed`, 신뢰도는 `high`, `medium`, `low`로 고정한다.
- 정확 해시, 제한적 포함 일치, 연속 2~5개 메시지 결합, 24시간과 프로젝트 점수를 규칙 기반으로 적용한다.
- 유일한 고신뢰 후보만 자동 확정하고 동점 후보는 모두 제안으로 남긴다.
- 관계 및 메시지 해시 인덱스는 기존 Capture 파일 저장 경계의 원자 JSON 인덱스로 확장한다. Knowledge 문서 그래프는 승인·거절 상태를 표현하지 못하므로 대체하지 않는다.
- 모바일 제어 API는 Bearer 키가 설정된 경우에만 활성화한다. 등록 프로젝트 조회, 세션 발견·요약, capture session 생성, 동의 기반 attach, sync, finalize, status만 허용한다.
- 프로젝트 등록 경로, 명령 실행, App Server 주소, 사용자 경로와 대화 원문은 모바일 API에서 반환하지 않는다.
- 관계 처리 실패는 Capture 저장을 되돌리지 않고 별도 최소 정보 재시도 작업으로 기록한다.

## 결과

거절 기억과 revision 재검증이 가능한 관계가 생기며 6단계 Viewer는 조회 API를 바로 사용할 수 있다. 모바일은 Windows 수집기에 제한된 작업만 지시하고 Codex App Server는 외부에 노출되지 않는다.

## 제외

Viewer 그래프 UI 개편, 임베딩, LLM 유사도, 원본 병합·삭제와 프로젝트 자동 재분류는 포함하지 않는다.
