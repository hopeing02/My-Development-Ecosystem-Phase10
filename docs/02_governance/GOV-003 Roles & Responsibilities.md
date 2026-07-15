# 📘 GOV-001
# 제3장 역할과 책임 (Roles & Responsibilities)

---

# 제18조 (목적)

본 장은 MDE(My Development Ecosystem)에 참여하는 모든 주체의 역할, 책임 및 권한을 정의한다.

모든 참여자는 자신의 역할에 맞는 책임을 수행하며, 다른 역할의 책임을 침해하지 않는다.

---

# 제19조 (참여 주체)

MDE는 다음의 세 가지 참여 주체로 구성된다.

### 1. User

전략 수립과 최종 의사결정을 담당한다.

### 2. AI Organization

프로젝트 수행을 지원하는 전문 Agent 조직이다.

### 3. Platform

Workflow, Knowledge, Automation 등 공통 서비스를 제공하는 기반 시스템이다.

---

# 제20조 (User의 역할)

User는 MDE의 최고 책임자이다.

### 주요 책임

- 프로젝트 목표 수립
- 요구사항 승인
- 우선순위 결정
- 아키텍처 승인
- 최종 품질 승인
- 릴리스 승인
- 거버넌스 정책 승인

### 권한

- 모든 프로젝트 생성 및 종료
- AI Agent 실행 승인
- 문서 승인
- 변경 승인
- 정책 개정

---

# 제21조 (AI Organization의 역할)

AI Organization은 User의 의사결정을 지원하며, 실행 업무를 담당한다.

### 주요 책임

- 요구사항 분석
- 설계 지원
- 코드 생성
- 테스트 생성
- 문서 작성
- 품질 검토
- Knowledge 등록

AI는 승인 권한을 갖지 않으며, 결과를 제안하는 역할을 수행한다.

---

# 제22조 (Agent Manager의 책임)

Agent Manager는 AI Organization을 총괄한다.

### 주요 업무

- 작업 분석
- 적합한 Agent 선택
- Workflow 생성
- 작업 분배
- 결과 통합
- 충돌 조정
- 사용자 보고

---

# 제23조 (Division별 책임)

### Planning Division

- 요구사항 분석
- 일정 계획
- 우선순위 정의
- 프로젝트 계획 수립

---

### Development Division

- Architecture
- Database
- API
- UI
- Source Code
- Test Code

---

### Knowledge Division

- 문서 관리
- Prompt 관리
- Template 관리
- Knowledge Base 관리

---

### Automation Division

- Workflow 관리
- Git 자동화
- Release 자동화
- Obsidian 연동
- 반복 작업 자동화

---

# 제24조 (Platform의 책임)

Platform은 공통 기능을 제공한다.

### 구성 요소

- Knowledge Platform
- Workflow Engine
- Command Engine
- Prompt Engine
- Memory Engine
- Automation Engine

### 책임

- 안정적인 운영
- 데이터 보존
- 검색 기능
- 버전 관리
- 로그 관리
- 권한 관리

---

# 제25조 (책임 분리 원칙)

모든 역할은 다음 원칙을 따른다.

1. 한 역할은 명확한 책임을 가진다.
2. 동일한 책임은 하나의 역할만 가진다.
3. 책임과 권한은 일치해야 한다.
4. 승인 권한은 User에게 있다.
5. AI는 실행과 제안을 담당한다.
6. Platform은 공통 서비스를 제공한다.

---

# 제26조 (협업 원칙)

프로젝트는 다음 순서로 협업한다.

```text
User
 ↓
Agent Manager
 ↓
Planning Division
 ↓
Development Division
 ↓
Knowledge Division
 ↓
Automation Division
 ↓
Platform
 ↓
User 승인
```

모든 결과는 User의 검토 및 승인 절차를 거친다.

---

# 제27조 (책임 평가)

각 역할은 다음 기준으로 평가한다.

### User

- 의사결정의 적절성
- 목표 달성률

### AI Organization

- 결과 품질
- 정확성
- 재사용성

### Platform

- 안정성
- 성능
- 가용성
- 확장성

평가 결과는 지속적인 개선에 반영한다.

---

## 자체 검토

✓ 참여 주체 정의 완료

✓ User 역할 정의 완료

✓ AI Organization 역할 정의 완료

✓ Platform 역할 정의 완료

✓ 협업 원칙 정의 완료

✓ 책임 평가 기준 정의 완료

**검토 결과 : 이상 없음**