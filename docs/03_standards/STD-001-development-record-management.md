# STD-001 개발 기록 관리 표준

- 문서 번호: STD-001
- 버전: 1.0.0
- 상태: Active
- 작성일: 2026-07-20
- 작성자: Codex
- 변경 이력: 1.0.0 — 개발일지, 의사결정, 변경 이력, 테스트 문서, AI 요청서 관리 규칙 제정

## 목적

개발 과정에서 생성되는 운영 기록의 형식과 저장 위치를 통일하여 변경 추적성과 재현성을 확보한다.

## 11. 개발일지 규칙

DevelopmentLog에는 다음 항목만 기록한다.

1. 오늘 작업
2. 문제점
3. 해결
4. 내일 작업
5. 소요시간

DevelopmentLog는 `docs/14_operations/DevelopmentLog/`에서 관리한다.

## 12. Decision Log 규칙

모든 중요한 설계 변경은 ADR로 기록한다.

다음과 같은 기술·도구 선택에는 선택 이유를 포함한다.

- 왜 Flutter인가?
- 왜 Apps Script인가?
- 왜 Markdown인가?
- 왜 Obsidian인가?

Decision Log는 `docs/09_decisions/`에서 관리한다.

## 13. Change Log 규칙

모든 버전 변경은 저장소 루트의 `CHANGELOG.md`에 기록한다.

각 버전에는 버전 번호와 변경 내용을 포함한다.

```text
v1.0.0
- 프로젝트 시작

v1.1.0
- 태그 기능 추가

v1.2.0
- GitHub 업로드 기능 추가
```

버전 번호는 Semantic Versioning을 따른다. 아직 릴리스되지 않은 변경은 `Unreleased`에 기록한다.

## 14. 테스트 규칙

모든 기능은 구현과 함께 테스트 문서를 작성한다.

- 테스트 문서는 `docs/12_test/` 또는 프로젝트별 `tests/` 문서 디렉터리에서 관리한다.
- 테스트 문서에는 대상, 사전 조건, 절차, 예상 결과, 실제 결과를 기록한다.
- 테스트 실행과 결과 기록이 없으면 기능을 완료로 처리하지 않는다.
- 문서·구조 변경은 링크, 경로, 필수 항목을 검증하는 문서 테스트로 대체할 수 있다.

## 15. AI 요청서 규칙

Codex, Claude Code, Gemini에 전달하는 모든 AI 요청서는 저장소 루트의 `11_AI_Request/`에서 관리한다.

AI 요청서에는 최소한 다음 내용을 기록한다.

- 요청 ID
- 작성일
- 대상 AI
- 목적
- 요청 내용
- 제약 조건
- 기대 결과
- 처리 상태

재사용 가능한 프롬프트 표준은 `docs/06_prompts/`에서 관리하고, 실제 작업 요청서는 `11_AI_Request/`에 보관한다.

## 관련 문서

- `CON-010 Documentation System`
- `CON-011 Change Management`
- `GOV-004 Decision-Making Framework`
- `GOV-006 AI Operations`
- `ADR-002 Operational Record Structure`
- `TEST-001 Operational Record Rules`

## 자체 검토 결과

- 개발일지 허용 항목을 5개로 제한했다.
- 중요한 설계 변경의 ADR 기록 의무를 정의했다.
- 모든 버전 변경의 CHANGELOG 기록 의무를 정의했다.
- 테스트 문서 없는 완료 처리를 금지했다.
- 세 AI 도구의 요청서 저장 위치를 통일했다.

검토 결과: 이상 없음
