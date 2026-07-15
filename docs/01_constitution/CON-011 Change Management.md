# 📘 CON-000
# 제11장 변경 관리 (Change Management)

---

## 제71조 (목적)

변경 관리(Change Management)의 목적은 MDE의 모든 자산을 일관성 있고 추적 가능하게 관리하는 것이다.

모든 변경은 기록되고 검토되며, 필요 시 이전 상태로 복원할 수 있어야 한다.

---

## 제72조 (변경 대상)

다음 자산은 변경 관리 대상에 포함한다.

### 문서

- Constitution
- Standards
- SDS
- Architecture
- API
- Database
- UI
- Prompt
- Template

### 개발 자산

- Source Code
- Library
- Plugin
- Workflow
- Script

### AI 자산

- Prompt Library
- Agent 정의
- Workflow 정의
- Command 정의
- Memory 설정

### Knowledge 자산

- Knowledge Base
- Error Library
- Development Log
- Learning Note

모든 변경은 동일한 절차를 따른다.

---

## 제73조 (변경 유형)

변경은 다음과 같이 분류한다.

### Major

구조나 정책이 변경되는 경우

예)

- Constitution 개정
- Architecture 변경
- 표준 변경

버전 증가

1.x → 2.0

---

### Minor

기능 추가 및 개선

예)

- 새로운 Template
- 새로운 Workflow
- 새로운 Prompt

버전 증가

1.2 → 1.3

---

### Patch

오류 수정

예)

- 오탈자
- 버그 수정
- 링크 수정

버전 증가

1.2.1 → 1.2.2

---

## 제74조 (변경 절차)

모든 변경은 다음 절차를 따른다.

```text id="v31krt"
변경 요청

↓

영향 분석

↓

설계 수정

↓

구현

↓

테스트

↓

문서 갱신

↓

리뷰

↓

승인

↓

배포

↓

Knowledge 등록
```

각 단계는 생략하지 않는 것을 원칙으로 한다.

---

## 제75조 (버전 정책)

MDE는 Semantic Versioning을 따른다.

형식

Major.Minor.Patch

예)

- 1.0.0
- 1.2.0
- 1.2.5
- 2.0.0

버전 변경 사유는 CHANGELOG에 기록한다.

---

## 제76조 (변경 이력)

모든 문서는 변경 이력을 포함한다.

기록 항목

- 버전
- 변경일
- 변경자
- 변경 내용
- 변경 이유
- 영향 범위

변경 이력은 삭제하지 않는다.

---

## 제77조 (AI 변경 관리)

AI가 생성하거나 수정한 내용도 변경 관리 대상이다.

AI 변경 시 다음 사항을 기록한다.

- 사용한 Agent
- 사용한 Prompt
- 변경 목적
- 검토 결과
- 승인 여부

AI 결과는 검토 후 적용하는 것을 원칙으로 한다.

---

## 제78조 (Git 운영 원칙)

모든 프로젝트는 Git 기반으로 관리한다.

기본 원칙

- 의미 있는 단위로 Commit
- 명확한 Commit Message
- Release Tag 관리
- Branch 전략 준수
- 변경 이력 보존

Git은 프로젝트의 공식 변경 기록으로 사용한다.

---

## 제79조 (릴리스 관리)

릴리스 전 다음 항목을 확인한다.

□ 테스트 완료

□ 문서 최신화

□ CHANGELOG 작성

□ 버전 업데이트

□ 태그 생성

□ 배포 검증

□ Knowledge 등록

릴리스 후 회고를 수행하고 개선 사항을 기록한다.

---

## 제80조 (지속적 개선)

변경 관리 절차는 정기적으로 검토한다.

다음 항목을 반영하여 개선한다.

- 프로젝트 경험
- 사용자 피드백
- AI 활용 결과
- 품질 지표
- 자동화 수준

모든 개선 사항은 표준 문서에 반영한다.

---

## 제11장 자체 검토

✓ 변경 대상 정의 완료

✓ 변경 유형 정의 완료

✓ 변경 절차 정의 완료

✓ 버전 정책 정의 완료

✓ AI 변경 관리 정의 완료

✓ Git 및 릴리스 원칙 정의 완료

**검토 결과 : 이상 없음**
