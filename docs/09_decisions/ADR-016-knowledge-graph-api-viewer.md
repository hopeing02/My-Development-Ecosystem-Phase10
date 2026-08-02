# ADR-016 Knowledge Graph API와 Viewer 통합

- 상태: Accepted (2026-07-30 편집 Command 확장)
- 결정일: 2026-07-27

## 배경

Knowledge Plugin은 Markdown 색인과 검색·백링크를 제공하지만 링크 대상 해석과
Source별 그래프 조회 계층이 없었다. AutoKnowledge Lite가 저장한 새 문서를 즉시
색인하는 공개 계약과, SQLite 또는 Vault에 직접 접근하지 않는 조회 중심 Viewer가
필요하다.

## 결정

- Knowledge Plugin을 문서 ID, 링크 해석과 그래프 관계의 단일 기준으로 유지한다.
- AutoKnowledge Lite는 MDE 내부 모듈이나 SQLite를 사용하지 않고 버전 `1` JSON
  CLI 계약만 호출한다.
- Graph Query API는 조회 전용으로 유지하고, 명시 저장에만 사용하는 Knowledge
  Command API를 분리한다. Command API는 원본 Markdown을 원자 저장한 뒤 단일 파일을
  재색인하며 SQLite를 직접 편집하지 않는다.
- API는 `mde knowledge serve`로 `127.0.0.1:8765`에 기본 바인딩한다. Android 연동 시 `--host`에는 비공개 LAN 또는 Tailscale
  IP 하나만 허용하고 공용 IP와 `0.0.0.0`은 거부한다.
- Command API는 loopback과 위에서 허용한 private/Tailscale IP의 동일 Origin 요청만
  허용한다. 따라서 Android Viewer는 연결한 서버 Origin에서만 편집할 수 있다.
- Knowledge Viewer는 `apps/knowledge-viewer/`의 React·TypeScript·Vite 앱으로
  관리하고 Graph API만 사용한다.
- Android Viewer는 `apps/knowledge-viewer/android/`에서 관리하며 동일한 Viewer를
  캐시 없는 동일 Origin WebView로 표시한다.
- personal과 work Source 데이터는 `confirmSensitive=true` 확인 없이는 API가
  반환하지 않는다.
- 실제 Markdown과 개인 Vault는 MDE 저장소 밖에 유지한다.

## 결과

AutoKnowledge Lite의 저장 실패와 색인 실패를 분리하면서 새 파일만 증분 색인할
수 있다. Viewer는 Source 전체 및 문서 중심 방향 그래프를 표시하며, Source 정책이
허용하고 사용자가 미리보기를 확인한 뒤 명시적으로 저장한 경우에만 원본 Markdown을
수정한다. 파일 저장 성공 뒤 재색인에 실패하면 파일은 유지하고 재색인을 재시도한다.

## 제외 범위

- AI 분석·추천·질의응답
- 벡터 DB와 의미 유사도 그래프
- 문서 삭제·이동·파일명 변경과 WYSIWYG 편집
- 로그인, 외부 공개와 클라우드 배포
