# CODE-001 Knowledge Plugin v1 구현 기록

- 버전: 1.0.0
- 상태: Implemented
- 작성일: 2026-07-22

## 구현 모듈

- `models.py`: Source, Document, Search, Scan 모델과 Category 기본값
- `paths.py`: 사용자 전역 데이터 위치
- `registry.py`: JSON Source 등록·조회·변경·해제
- `parser.py`: Markdown 및 Obsidian 문법 추출
- `scanner.py`: 읽기 전용 재귀 스캔과 제외 규칙
- `repository.py`: SQLite, FTS5/LIKE, 태그, 링크, 백링크
- `service.py`: 증분 색인과 민감 Source/Agent 정책
- `cli.py`: add/list/show/update/remove/scan/search/backlinks

## 제한

서버, UI, AI 질의응답, 벡터 검색, 감시, 동기화, 편집, 자동 Git 기능은 없다. 첨부파일은 링크만 기록하고 본문을 색인하지 않는다. Source 간 링크를 자동 해석하지 않는다.
