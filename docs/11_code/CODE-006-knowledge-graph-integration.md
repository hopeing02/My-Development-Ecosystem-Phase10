# CODE-006 Knowledge Graph 통합 구현

- 작성일: 2026-07-27
- 상태: Complete

## 구현

- Source별 캡처 쓰기 정책과 버전 `1` JSON CLI 계약
- 안전한 단일 Markdown 색인과 Added/Updated/Unchanged 판정
- resolved/unresolved/ambiguous 링크 해석
- 전체·문서 중심 `KnowledgeGraphService`
- 조회용 FastAPI Graph API, 로컬 전용 Command API와 serve 명령
- React·TypeScript·Vite·Cytoscape.js Knowledge Viewer
- 연결도 우선 그래프 제한, 잘림 메타데이터와 안전한 2,000자 미리보기
- 검색 디바운스·태그 개수·끊어진 링크 가상 노드·문서 관계 탐색 UI
- 설치 가능한 PWA 매니페스트·아이콘·API 비캐시 서비스 워커
- 서버 자동 시작과 Edge 앱 모드를 제공하는 Windows 실행 스크립트
- 서버 주소 검증·동일 Origin 제한·캐시 제거를 적용한 Android WebView 앱
- 비공개 IP 한정 `--host` 바인딩과 API `no-store` 응답 헤더
- 고정 Android APK 한 파일만 제공하는 휴대폰 다운로드 엔드포인트
- `mde-core`에 포함되는 production Viewer 정적 자산
- AutoKnowledge Lite subprocess 클라이언트, 원자 저장과 색인 재시도
- frontmatter·fenced/inline code 영역을 제외하는 링크 parser와 occurrence 위치 추적
- Source별 Viewer 편집·링크 재작성 정책, contentHash 충돌 검사와 2MB 제한
- unknown frontmatter 필드 보존, UTF-8 BOM 유지, 임시 파일 검증·백업·원자 replace
- 문서 편집·변경 미리보기·링크 대상 검색/미리보기·색인 재시도 UI

AutoKnowledge Lite와 Viewer는 Knowledge SQLite를 직접 읽거나 수정하지 않는다.
Viewer 저장은 Command API를 통해 원본 Markdown을 먼저 수정하고 Knowledge Plugin이
SQLite·FTS·태그·백링크·그래프 관계를 다시 만든다.
