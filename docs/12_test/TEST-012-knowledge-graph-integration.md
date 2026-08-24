# TEST-012 Knowledge Graph 통합 검증

- 작성일: 2026-07-29
- 상태: Passed

## 검증 범위

- 단일 파일 색인과 경로 탈출 차단
- 민감 Source 캡처 쓰기 확인
- 링크 방향, 중복 후보, 끊어진 링크와 고아 문서
- 깊이 1~3, 방향 필터와 순환 그래프
- Graph API 응답·오류·민감 Source 정책
- Viewer Source 선택·문서 상세·민감 Source 확인
- Graph 제한·잘림 상태, 태그 개수, 표시명·heading 보존과 안전한 미리보기
- Viewer 비민감 자동 선택, 400ms 검색 디바운스와 검색 결과 중심 이동
- Viewer 설치 프롬프트, PWA 매니페스트와 Graph API 비캐시 정책
- 매니페스트·서비스 워커·아이콘 HTTP 제공과 Windows 실행 스크립트 구문
- Android 서버 주소 정규화·외부 Origin 차단과 Debug APK 빌드
- 비공개 IP 허용, 공용·전체 인터페이스 거부와 API `no-store` 헤더
- AutoKnowledge 저장·MDE 미설치·색인 실패 원본 유지·재시도
- frontmatter tags/aliases 및 fenced/inline code 링크 오탐 방지
- 문서 편집 미리보기, unknown frontmatter·BOM 보존, 백업과 원자 저장
- contentHash 충돌 시 원본 불변, 읽기 전용 Source와 경로 탈출 차단
- 동일 링크 다중 occurrence 중 선택 항목만 재작성, 재색인과 백링크 갱신
- Viewer 편집·변경 미리보기·링크 검색/미리보기/명시 저장

## 최종 결과

- MDE 전체: `178 passed`
- AutoKnowledge Lite: `73 passed`
- Knowledge 전용: `61 passed`
- Knowledge Viewer: `17 passed`
- Graph API·서버 호스트 집중 테스트: `12 passed`
- Android JVM 단위 테스트: `3 passed`
- Android Debug APK: `assembleDebug` 성공
- Android APK 고정 다운로드·누락 404·원본 SHA-256 일치
- production build: 성공
- 격리 로컬 서버 HTTP E2E: 편집 미리보기·저장·재색인·링크 occurrence 연결·
  백링크·Graph Edge 갱신 통과
- Viewer UI 컴포넌트 E2E: 명시 저장, 변경 미리보기, 대상 검색·링크 연결 통과
- Ruff: 통과
- 변경 범위 formatter: 통과

## 성능 기준

로컬 임시 SQLite의 문서 1,000개와 해석된 Edge 5,000개 기준:

- 전체 Source 그래프: `388.18 ms`
- 문서 중심 depth 2, 반환 문서 21개: `290.92 ms`
- 검색: `335.51 ms`
- 문서 상세: `418.13 ms`

최종 전체 테스트와 빌드 결과는 DevelopmentLog와 작업 제출 보고서에 기록한다.
