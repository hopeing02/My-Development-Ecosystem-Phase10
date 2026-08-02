# SDS-003 Knowledge Graph 통합

- 버전: 1.0.0
- 상태: Implemented

## 구성

```text
AutoKnowledge Lite → JSON CLI → Knowledge Plugin
Knowledge Viewer → Graph API → Graph Query Service → Knowledge Repository
Knowledge Viewer → Command API → Document Command Service → Markdown 원자 저장 → 단일 파일 재색인
Android Viewer → 비공개 LAN/Tailscale → Knowledge Viewer → Graph API
```

## 링크 해석

같은 Source 안에서 상대경로, 확장자 보완 경로, stem, title, aliases 순서로
해석한다. 단일 후보는 `resolved`, 후보 없음은 `unresolved`, 복수 후보는
`ambiguous`로 기록한다. 링크 방향은 작성 문서에서 대상 문서로 향한다.

## Graph Query

- Source 전체 그래프와 문서 중심 그래프
- 깊이 1~3 및 incoming/outgoing/both
- 고아 문서, 끊어진 링크와 중복 후보
- Source 그래프 최대 1,000개, 문서 중심 그래프 최대 300개 노드
- 순환 링크에서 방문 노드를 중복 처리하지 않는 BFS
- 전체 그래프는 연결 수, 수정 시각 순으로 제한하고 `totalDocumentCount`,
  `returnedDocumentCount`, `truncated`를 반환

## SQLite 링크 계약

`knowledge_links`는 원문 대상, 정규화 대상, heading, 표시명, 해석 문서 ID,
`resolution_status`, `is_resolved`, 생성 시각을 보존한다. 기존 DB에는 시작 시
호환 마이그레이션을 적용한다. 링크 occurrence ID, raw text, offset, line, column과
문맥도 저장해 동일한 링크 문자열의 여러 출현을 구분한다. 외부 URL과 첨부는 기본
문서 그래프 Edge에서 제외한다.

## 공개 계약

- CLI: `integration-info`, `list`, `source-path`, `index-file --format json`
- API: `/api/v1/knowledge/...`
- Command API: `preview-update`, `PATCH document`, `link-resolutions`, `reindex`
- 모든 기계 응답: `apiVersion="1"`, `success`
- JSON 오류에는 코드·메시지·details만 포함하며 traceback은 포함하지 않는다.
- Graph API는 OpenAPI 문서 엔드포인트를 공개하지 않으며 Viewer 정적 빌드를
  `mde-core` 패키지 자산으로 제공한다.

## 보안

단일 파일 색인은 등록 Source의 resolve된 내부 Markdown만 허용한다. 절대경로,
경로 탈출, 심볼릭 링크 탈출과 비 Markdown을 거부한다. 민감 Source API 조회는
명시적 확인을 요구하며 Viewer는 데이터를 localStorage에 저장하지 않는다.
Command API는 loopback 또는 서버가 허용한 private LAN/Tailscale Host와 동일 Origin,
JSON Content-Type, 2MB 요청 제한, Source 편집 정책,
현재 파일 contentHash와 Source 내부 resolve 경로를 검증한다. 백업은 Source의
`.mde-backups/YYYY-MM-DD/` 아래에 문서당 최근 10개를 보관하며 Scanner가 제외한다.
Android 앱은 서버 주소만 저장하고 WebView 캐시와 외부 Origin 이동을 차단한다.
서버의 비로컬 바인딩은 공용·전체 인터페이스가 아닌 비공개 LAN 또는 Tailscale
IP 하나를 명시한 경우에만 허용한다. 모든 `/api/` 응답은 `Cache-Control: no-store`다.
