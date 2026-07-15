# 📘 GOV-001
# 제10장 변경 관리 (Change Management)

---

# 제91조 (목적)

본 장은 MDE(My Development Ecosystem) 내 모든 문서, 코드, AI Agent, Workflow, Knowledge 자산의 변경을 통제하고, 일관성과 안정성을 유지하기 위한 기준을 정의한다.

변경 관리는 단순 기록이 아니라 **시스템 진화의 제어 장치**이다.

---

# 제92조 (변경 대상)

다음 항목은 모두 변경 관리 대상이다.

- CON / GOV / STD 문서
- SDS / Architecture / API / DB 설계
- Source Code
- Prompt / Command / Agent 정의
- Workflow / Automation
- Knowledge Base
- Git Repository 구조
- Obsidian Vault 구조

---

# 제93조 (변경 유형)

변경은 다음 3가지로 분류한다.

---

## 1. Major Change (구조 변경)

시스템 구조 자체가 변경되는 경우

예:
- GOV 구조 변경
- Architecture 재설계
- CMD 체계 변경
- AI Agent 구조 변경

버전 증가:
```text id="major"
1.0 → 2.0
```

---

## 2. Minor Change (기능 변경)

기능 추가 또는 개선

예:
- 새로운 Command 추가
- Prompt 개선
- Workflow 추가
- API 확장

버전 증가:
```text id="minor"
1.1 → 1.2
```

---

## 3. Patch Change (수정)

버그 수정 또는 정리

예:
- 오타 수정
- 로직 수정
- 링크 수정
- 구조 정리

버전 증가:
```text id="patch"
1.1.1 → 1.1.2
```

---

# 제94조 (변경 절차)

모든 변경은 다음 절차를 따른다.

```text id="change-flow"
변경 요청
    ↓
영향 분석
    ↓
AI 검토
    ↓
Agent 검토
    ↓
User 승인
    ↓
수정 실행
    ↓
테스트
    ↓
Git 반영
    ↓
Knowledge 등록
```

---

# 제95조 (버전 관리)

모든 주요 산출물은 Semantic Versioning을 따른다.

형식:

```text id="version"
MAJOR.MINOR.PATCH
```

예:
- CON-000 v1.0.0
- GOV-001 v1.2.3
- SDS-005 v0.3.0

---

# 제96조 (변경 기록)

모든 변경은 반드시 기록되어야 한다.

기록 항목:

- 변경 내용
- 변경 이유
- 변경자 (User / AI / Agent)
- 영향 범위
- 이전 버전
- 변경 일자

---

# 제97조 (호환성 원칙)

변경 시 다음을 반드시 고려한다.

### 1. 하위 호환성 유지

기존 프로젝트가 깨지지 않아야 한다.

---

### 2. 연결성 유지

문서 간 링크가 유지되어야 한다.

---

### 3. Knowledge 연속성 유지

기존 Knowledge가 무효화되지 않아야 한다.

---

# 제98조 (롤백 정책)

문제 발생 시 이전 상태로 복구할 수 있어야 한다.

롤백 조건:

- 시스템 오류 발생
- 구조 충돌 발생
- 데이터 손실
- AI 판단 오류

---

# 제99조 (AI 변경 권한)

AI는 다음 변경을 제안할 수 있다.

허용:
- 코드 수정
- 문서 개선
- Prompt 개선
- Workflow 개선

불가:
- CON 변경
- GOV 변경
- 구조적 변경
- 릴리스 확정

---

# 제100조 (변경 안정성 규칙)

변경은 다음 원칙을 따른다.

1. 최소 변경 원칙
2. 영향 최소화 원칙
3. 테스트 우선 원칙
4. 기록 필수 원칙
5. 승인 기반 원칙

---

## 제10장 자체 검토

✓ 변경 유형 정의 완료

✓ 버전 체계 정의 완료

✓ 변경 절차 정의 완료

✓ 롤백 정책 정의 완료

✓ AI 권한 범위 정의 완료

**검토 결과 : 이상 없음**