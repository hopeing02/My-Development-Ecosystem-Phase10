# TEST-009 Capture Viewer와 지식 그래프 통합

- 실행일: 2026-08-03
- 상태: Passed (자동 테스트), 실제 기기 검증 대기

## 자동 검증

- Capture 목록 복합 필터, 검색 일치 위치, 정렬과 cursor pagination
- development_session 상세, 명령·Diff 지연 조회, 파일 경로 정규화와 변경 이력
- 사용자 메타데이터와 수집 원본 분리
- 프로젝트·파일·명령·테스트 그래프와 depth
- 문서 Capture 백링크 relation type
- 기존 Capture 저장·관계 회귀 테스트
- Knowledge Graph API 전체 회귀 및 loopback gateway
- Capture UI 배지·필터·세션 탭 lazy loading·관계 확정
- TypeScript production build

## 로컬 성능 측정

300개 development session, 세션당 메시지 10개·명령/파일/테스트 각 1개인 합성
projection에서 20회 측정한 p95는 목록 36.16ms, 검색 39.45ms, 프로젝트 그래프
49.02ms였다. 이는 서비스 계층 측정이며 브라우저·네트워크·실제 디스크 규모를 포함한
end-to-end 기준은 실제 Vault에서 별도 관찰해야 한다.

## 수동 검증 필요

실제 Android 클립보드 수집과 Windows Codex 세션이 존재하는 사용자 환경에서
양방향 Viewer 이동, 모바일 WebView 레이아웃과 150-node 실제 그래프 시간을 확인해야
한다. 저장소 테스트 fixture는 동일 데이터 흐름을 검증하지만 실제 기기 검증을
대체하지 않는다.
