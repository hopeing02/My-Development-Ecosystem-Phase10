# 📘 GOV-001
# 제6장 AI 운영 (AI Operations)

---

# 제48조 (목적)

본 장은 MDE(My Development Ecosystem)에서 AI Organization의 운영 원칙, 역할, 실행 절차 및 관리 기준을 정의한다.

AI는 단순한 도구가 아니라 프로젝트를 지원하는 전문 조직으로 운영한다.

---

# 제49조 (AI 운영 원칙)

AI는 다음 원칙을 따른다.

1. 역할 기반 운영(Role-Based AI)
2. Workflow 중심 협업
3. 표준 우선(Standard First)
4. Knowledge 활용(Knowledge First)
5. 사람 중심 승인(Human Approval)
6. 지속적인 개선(Continuous Improvement)

---

# 제50조 (AI Organization 구성)

AI Organization은 다음 계층으로 구성한다.

```text id="ai-layer-001"
User
  │
Agent Manager
  │
Planning Agents
Development Agents
Knowledge Agents
Automation Agents
Quality Agents
```

모든 Agent는 Agent Manager를 통해 작업을 배정받는다.

---

# 제51조 (Agent 생명주기)

모든 Agent는 다음 생명주기를 따른다.

```text id="agent-life-001"
생성(Create)
    ↓
초기화(Initialize)
    ↓
작업 할당(Assign)
    ↓
실행(Execute)
    ↓
검토(Review)
    ↓
결과 제출(Deliver)
    ↓
평가(Evaluate)
    ↓
종료(Archive)
```

실행 결과와 평가 내용은 Knowledge Platform에 기록한다.

---

# 제52조 (Agent 협업)

Agent는 단독으로 동작하지 않는다.

협업 원칙

- 역할 분담
- 입력/출력 명확화
- Workflow 준수
- 결과 공유
- 중복 작업 방지
- 충돌 시 Agent Manager 조정

---

# 제53조 (AI 권한)

AI는 다음 작업을 수행할 수 있다.

허용

- 요구사항 분석
- 문서 작성
- 설계 제안
- 코드 생성
- 테스트 생성
- 리뷰
- 품질 점검
- Knowledge 추천

제한

- 최종 승인
- 정책 변경
- 릴리스 승인
- 헌법(CON) 수정

---

# 제54조 (Prompt 운영)

모든 Agent는 표준 Prompt를 사용한다.

Prompt는 다음 요소를 포함한다.

- 역할(Role)
- 목표(Objective)
- 입력(Input)
- 출력(Output)
- 제약사항(Constraints)
- 품질 기준(Quality Criteria)

Prompt 변경은 버전 관리 대상이다.

---

# 제55조 (AI 품질 관리)

AI 산출물은 다음 기준으로 평가한다.

□ 정확성

□ 완전성

□ 표준 준수

□ 재사용성

□ 유지보수성

□ 문서 일치성

□ 테스트 가능성

품질 평가 결과는 Knowledge Platform에 저장한다.

---

# 제56조 (AI 성능 개선)

AI 운영 결과를 지속적으로 분석한다.

평가 항목

- 작업 성공률
- 재작업 비율
- 사용자 승인율
- Workflow 완료 시간
- Prompt 재사용률

분석 결과는 Prompt와 Workflow 개선에 활용한다.

---

# 제57조 (AI 감사)

AI 활동은 감사(Audit) 대상이다.

기록 항목

- 사용 Agent
- 사용 Prompt
- 실행 시간
- 입력 데이터
- 출력 결과
- 승인 여부
- 관련 문서

감사 기록은 변경 이력과 함께 보관한다.

---

## 제6장 자체 검토

✓ AI 운영 원칙 정의 완료

✓ Agent 생명주기 정의 완료

✓ 협업 구조 정의 완료

✓ Prompt 운영 기준 정의 완료

✓ 품질 및 감사 기준 정의 완료

**검토 결과 : 이상 없음**