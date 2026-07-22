# ADR-002 운영 기록 저장 구조

- 문서 번호: ADR-002
- 버전: 1.0.0
- 상태: Accepted
- 작성일: 2026-07-20
- 작성자: Codex

## 결정

- DevelopmentLog는 `docs/14_operations/DevelopmentLog/`에 저장한다.
- 중요한 설계 결정은 `docs/09_decisions/`에 ADR로 저장한다.
- 버전 변경은 저장소 루트의 `CHANGELOG.md`에 저장한다.
- 테스트 문서는 `docs/12_test/` 또는 프로젝트별 테스트 문서 디렉터리에 저장한다.
- Codex, Claude Code, Gemini의 실제 요청서는 저장소 루트의 `11_AI_Request/`에 저장한다.

## 이유

기존 MDE 문서 흐름을 유지하면서 운영 기록을 각 책임 영역에 배치하기 위해서다. 재사용 가능한 프롬프트 표준과 개별 실행 요청을 분리하면 표준 문서와 감사 기록의 역할이 명확해진다.

## 검토한 대안

### 모든 기록을 한 디렉터리에 저장

기록 유형별 책임과 기존 문서 흐름이 불명확해지므로 채택하지 않았다.

### AI 요청서를 `docs/06_prompts/`에 저장

`PRM`은 재사용 가능한 프롬프트 표준이고 AI 요청서는 개별 실행 기록이므로 채택하지 않았다.

## 영향

- 운영 기록의 위치가 고정된다.
- AI 요청 추적과 공급자별 템플릿 재사용이 가능해진다.
- 기능 완료 전 테스트 문서 확인이 필수 단계가 된다.

## 관련 문서

- `STD-001 Development Record Management`
- `PRM-001 AI Prompt System`
- `TEST-001 Operational Record Rules`

## 자체 검토 결과

결정, 이유, 대안, 영향과 관련 문서를 기록했다.

검토 결과: 이상 없음
