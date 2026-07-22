# RELEASE-001 MDE Knowledge Plugin v1

- 버전: 1.0.0
- 상태: Ready
- 작성일: 2026-07-22

## 제공 기능

외부 Markdown/Obsidian Source 등록, 사용자 전역 설정, 로컬 SQLite 색인, 텍스트·Source·Category·태그 검색, 링크·백링크, 증분 스캔, 민감 Source 보호와 Agent 차단을 제공한다.

## 호환성

기존 MDE 명령과 Workflow/Task/Agent/AI/Sync 테스트를 포함한 전체 131개 테스트가 통과했다. Knowledge 기능을 사용하지 않으면 사용자 데이터 디렉터리나 DB를 생성하지 않는다.

## 다음 버전 후보

- development/personal/work 프로필별 DB
- SQLite 암호화 검토
- 안전한 Source 간 명시적 링크
- 첨부파일 메타데이터 색인

AI 질의응답, 벡터 검색, 서버, 동기화는 자동으로 다음 버전에 포함하지 않는다.
