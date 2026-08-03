# CODE-009 Capture Viewer와 지식 그래프 통합

- 구현일: 2026-08-03
- 상태: Implemented

## 구현

- `CaptureQueryService`로 목록·검색·상세·하위 자료·파일 이력·문서 Capture 백링크와
  근거 기반 그래프를 제공한다.
- 기존 `CaptureRelationRepository` projection을 확장해 검증 완료된 세션 payload를
  보존한다.
- Knowledge Viewer에 문서/Capture 내비게이션, 자연어 배지, 복합 필터, 유형별 상세,
  지연 탭, 관계 관리와 Capture 그래프를 추가한다.
- Knowledge Viewer 서버가 loopback Capture API를 제한적으로 gateway하고 실행
  스크립트가 두 서비스를 준비한다.
- 모바일 breakpoint, 44px 터치 영역, focus-visible, tab ARIA와 관계 설명을 적용한다.

## 원본 정책

수집된 대화·명령·파일·Diff·테스트는 UI와 수정 모델에서 제외해 읽기 전용으로
유지한다. 사용자 편집 정보는 별도 파일에 저장한다. 절대 경로는 `%REPO_ROOT%`
별칭 또는 안전한 파일명으로 변환한다.

