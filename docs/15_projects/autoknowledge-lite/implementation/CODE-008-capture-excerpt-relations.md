# CODE-008 Capture 발췌 관계와 모바일 Codex 저장

- 구현일: 2026-08-03
- 범위: AutoKnowledge Capture 통합 개발 5단계

`capture_relations.py`에 관계 모델, 원자 저장소, 메시지 해시 matching 인덱스, 정확·포함·연속 메시지 matcher, 점수, 상태 전이, revision 재검증, Backfill과 API를 구현했다. Capture 서비스 후처리에서 관계 작업을 호출하되 실패는 warning과 별도 retry job으로 격리한다.

`codex_control.py`는 인증된 최소 권한 모바일 API를 제공한다. Android 앱에는 PC 연결, 등록 프로젝트와 실제 세션 선택, 전체 공개 대화 동의, attach/sync/finalize/status와 Viewer 열기 UI를 기존 Clipboard Capture와 독립적으로 추가했다.
