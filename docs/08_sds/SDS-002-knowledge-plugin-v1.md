# SDS-002 Knowledge Plugin v1

- 버전: 1.0.0
- 상태: Implemented
- 작성일: 2026-07-22

## Source 모델

Category는 `development`, `project`, `personal`, `work`, `shared`이며 Type은 `markdown`, `obsidian`이다. personal과 work는 `sensitive=true`, `allow_agent_access=false`가 기본값이다.

## 저장 위치

- Source Registry: `%MDE_DATA_HOME%/knowledge/sources.json` 또는 `~/.mde/knowledge/sources.json`
- SQLite: `%MDE_DATA_HOME%/knowledge/knowledge.db` 또는 `~/.mde/knowledge/knowledge.db`
- Audit Log: `%MDE_DATA_HOME%/knowledge/logs/knowledge-YYYY-MM-DD.log` 또는 `~/.mde/knowledge/logs/knowledge-YYYY-MM-DD.log`

두 위치 모두 프로젝트 저장소 밖의 사용자 전용 경로가 기본값이다.

## SQLite 스키마

- `knowledge_sources`
- `knowledge_documents`
- `knowledge_tags`
- `knowledge_links`
- `knowledge_scan_history`
- `knowledge_fts` — FTS5 지원 시 생성, 미지원 시 LIKE 검색

모든 문서·태그·링크·스캔 기록은 `source_id`를 가진다.

## 처리

- `*.md`를 재귀 탐색하며 도구·설정·빌드 디렉터리를 제외한다.
- UTF-8과 UTF-8 BOM을 지원하고 파일별 오류 후 계속 진행한다.
- frontmatter title/tags/aliases, H1, 본문 태그, Markdown/위키/첨부 링크를 추출한다.
- 콘텐츠 SHA-256으로 Added, Updated, Deleted, Unchanged를 판정한다.
- 원본 파일은 읽기만 하며 제거 명령은 등록과 색인만 삭제한다.

## 보안

기본 검색과 전체 스캔은 민감 Source를 제외한다. Source를 명시하면 일반 CLI에서 민감 Source를 검색·스캔할 수 있다. Agent 조회는 `enabled=true`, `allow_agent_access=true`, `sensitive=false`를 모두 요구한다.

SQLite에는 원문 전체가 평문으로 저장될 수 있으며 v1은 데이터베이스 암호화를 제공하지 않는다.

## 감사 로그

JSON Lines 형식으로 `source.added`, `source.updated`, `source.removed`, `scan.started`, `scan.completed`, `scan.failed` 이벤트를 기록한다. Source ID·이름·Category·민감 여부, 설정 변경값, 스캔 건수, 오류 상대경로와 오류 유형만 허용한다. 검색어·검색 결과·문서 본문·Source 절대경로는 금지한다.

감사 이벤트를 기록하기 전에 30일 보존 경계를 지난 `knowledge-YYYY-MM-DD.log`만 자동 삭제한다. 오늘을 포함한 최근 30일 로그는 유지한다. 다른 파일명, 디렉터리, 심볼릭 링크와 원본 Source 파일은 삭제하지 않는다.
