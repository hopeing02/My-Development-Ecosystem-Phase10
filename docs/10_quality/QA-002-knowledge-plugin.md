# QA-002 Knowledge Plugin 품질 기준

- 버전: 1.0.0
- 상태: Passed
- 작성일: 2026-07-22

## 기준

- 원본 파일 쓰기·이동·삭제 코드 없음
- 네트워크·AI·클라우드 코드 없음
- 민감 Source 기본 검색·스캔·Agent 접근 차단
- Source별 SQLite 격리
- 파일별 오류 격리
- FTS5 미지원 시 LIKE 대체
- 기존 MDE CLI 회귀 없음
- 테스트, Ruff, 변경 파일 포맷 검사 통과

## 결과

- 전체 pytest: 131 passed
- Ruff: 제외된 외부 임시 디렉터리를 제외한 저장소 검사 통과
- 변경 파일 formatter: 통과
- mypy: 설정과 설치가 없어 실행 대상 아님
