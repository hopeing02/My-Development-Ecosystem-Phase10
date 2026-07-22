# ARCH-001 MDE Knowledge Plugin Architecture

- 버전: 1.0.0
- 상태: Active
- 작성일: 2026-07-22

## 목적

MDE 내부에 분리 가능한 로컬 지식 색인 기능을 제공한다. 독립 애플리케이션, 서버, 네트워크 전송 기능은 만들지 않는다.

## 구조

```text
MDE CLI
  └ mde.knowledge
      ├ SourceRegistry  → ~/.mde/knowledge/sources.json
      ├ Scanner/Parser  → 외부 Markdown Source 읽기 전용 접근
      ├ Repository      → ~/.mde/knowledge/knowledge.db
      ├ Audit Logger    → ~/.mde/knowledge/logs/knowledge-YYYY-MM-DD.log
      └ Service         → 검색·태그·백링크·증분 색인·접근 정책
```

원본 Source는 MDE 저장소에 복사하지 않는다. 모든 테이블과 변경 쿼리는 `source_id`로 격리한다. Agent 통합은 안전한 조회 함수까지만 제공하며 자동 프롬프트 삽입은 하지 않는다.

감사 로그에는 Source 생명주기와 스캔 결과만 기록한다. 검색어, 검색 결과, 문서 본문과 Source 절대경로는 기록하지 않는다.

## 의존성

표준 라이브러리와 기존 PyYAML만 사용한다. 외부 AI, 클라우드, 웹, 벡터 데이터베이스 의존성은 없다.

## 자체 검토

기존 Core 변경은 CLI 등록과 dispatch로 제한되며 기존 Workflow Plugin 인터페이스는 변경하지 않았다.
