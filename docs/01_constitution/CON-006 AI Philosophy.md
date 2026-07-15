# 📘 CON-000
# 제6장 AI 철학 (AI Philosophy)

---

## 제28조 (AI의 역할)

My Development Ecosystem(MDE)에서 AI는 단순한 코드 생성 도구가 아니다.

AI는 프로젝트 수행을 지원하는 **전문 역할(Agent)** 을 가진 협업 파트너이다.

AI의 목적은 사용자를 대신하여 의사결정을 하는 것이 아니라, 분석·설계·구현·검토를 지원하여 개발자의 생산성과 품질을 향상시키는 것이다.

---

## 제29조 (AI 협업 원칙)

MDE는 다음 원칙에 따라 AI를 활용한다.

### 원칙 1. Human in Control

최종 의사결정은 항상 사용자가 수행한다.

AI는 여러 대안을 제시하고, 사용자의 판단을 지원한다.

---

### 원칙 2. Role-Based AI

AI는 역할별 Agent로 구성한다.

예시

- Project Manager Agent
- Business Analyst Agent
- Planner Agent
- Architect Agent
- UI Designer Agent
- Database Designer Agent
- API Designer Agent
- Developer Agent
- Reviewer Agent
- Tester Agent
- Documentation Agent
- Knowledge Manager Agent
- Release Manager Agent

각 Agent는 명확한 책임과 산출물을 가진다.

---

### 원칙 3. Collaboration First

AI Agent는 독립적으로 동작하지 않는다.

Workflow Engine의 관리 아래 서로 협업하며 프로젝트를 수행한다.

예)

요구사항 분석

↓

아키텍처 설계

↓

DB 설계

↓

API 설계

↓

코드 생성

↓

리뷰

↓

테스트

↓

문서 생성

---

### 원칙 4. Explainability

AI는 가능한 한 결과의 근거와 이유를 함께 제공한다.

설계 변경, 코드 수정, 리뷰 의견 등은 추적 가능한 형태로 기록한다.

---

### 원칙 5. Continuous Learning

프로젝트에서 얻은 경험은 Knowledge Platform에 저장한다.

다음 프로젝트에서는 저장된 자산을 우선 활용하여 일관성과 재사용성을 높인다.

---

## 제30조 (AI의 책임)

AI는 다음 업무를 지원한다.

- 요구사항 분석
- 프로젝트 계획
- 시스템 설계
- UI 설계
- API 설계
- 데이터 구조 설계
- 코드 생성
- 코드 리뷰
- 테스트 생성
- 문서 생성
- 지식 정리
- 반복 작업 자동화

AI는 지원 역할을 수행하며, 승인과 배포는 사용자 또는 정의된 워크플로에 따른다.

---

## 제31조 (AI 운영 모델)

AI는 다음 구조로 운영한다.

사용자

↓

Command Engine

↓

Workflow Engine

↓

Agent Manager

↓

전문 Agent

↓

Knowledge Platform

↓

결과 반환

모든 AI 요청은 Workflow를 통해 관리하며, 수행 결과는 필요에 따라 지식 저장소에 기록한다.

---

## 제32조 (AI 품질 원칙)

AI가 생성한 결과물은 다음 기준으로 검토한다.

□ 요구사항 충족

□ 표준 준수

□ 문서 일관성

□ 코드 품질

□ 테스트 가능성

□ 유지보수성

□ 재사용성

□ 보안 고려

□ 변경 이력 기록

검토가 필요한 경우 Reviewer Agent 또는 사용자가 확인한다.

---

## 제33조 (AI 확장성)

MDE는 특정 AI 서비스에 종속되지 않는다.

새로운 AI 모델이 등장하면 Plugin 구조를 통해 통합할 수 있도록 설계한다.

예)

- ChatGPT
- Claude
- Gemini
- Codex
- Local LLM

AI 교체 시 Core Architecture는 변경하지 않는 것을 원칙으로 한다.

---

## 제34조 (AI 윤리)

MDE는 다음 원칙을 따른다.

- 사용자의 의도를 존중한다.
- 결과의 출처와 변경 이력을 관리한다.
- AI가 생성한 결과는 검토를 거쳐 사용한다.
- 자동화보다 정확성과 안전성을 우선한다.
- AI는 사용자의 학습과 성장을 돕는 방향으로 활용한다.

---

## 제6장 자체 검토

✓ AI 역할 정의 완료

✓ AI 협업 원칙 정의 완료

✓ Agent 구조 정의 완료

✓ AI 품질 기준 정의 완료

✓ AI 확장성 및 윤리 원칙 정의 완료

**검토 결과 : 이상 없음**
