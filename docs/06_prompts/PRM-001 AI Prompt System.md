# 📘 PRM-001
# AI Prompt System (프롬프트 표준 체계)

---

# 제1조 (목적)

본 문서는 MDE(My Development Ecosystem)에서 CMD 명령을 AI가 실제 실행 가능한 형태로 변환하기 위한 표준 프롬프트 구조를 정의한다.

PRM은 AI의 “사고 엔진”이며, 모든 실행의 내부 로직이다.

---

# 제2조 (PRM의 역할)

PRM은 다음 기능을 수행한다.

- CMD → 실행 가능한 작업으로 변환
- AI 사고 구조 표준화
- Agent 작업 분해
- Output 형식 강제
- 품질 기준 적용
- Workflow 생성

---

# 제3조 (PRM 구조)

모든 프롬프트는 다음 구조를 따른다.

```text id="prm-structure"
[ROLE]
[OBJECTIVE]
[CONTEXT]
[INPUT]
[PROCESS]
[OUTPUT FORMAT]
[CONSTRAINTS]
[QUALITY CHECK]
```

---

# 제4조 (표준 PRM 템플릿)

## 1. Role (역할)

AI의 역할 정의

예:
- System Architect
- Developer
- Reviewer
- Planner
- Knowledge Manager

---

## 2. Objective (목표)

무엇을 달성할 것인가

예:
- SDS 생성
- 코드 생성
- 문서 작성
- 시스템 설계

---

## 3. Context (맥락)

현재 상태 정보

예:
- 프로젝트 구조
- 기존 GOV/STD/CMD
- 사용자 요구사항

---

## 4. Input (입력)

CMD에서 전달된 데이터

예:
```text id="input-example"
/build AutoKnowledge-Lite
```

---

## 5. Process (처리 방식)

AI 사고 과정 정의

- 분석
- 분해
- 설계
- 생성
- 검증

---

## 6. Output Format (출력 형식)

결과 구조 강제

예:
- Markdown
- JSON
- Code Block
- Document Structure

---

## 7. Constraints (제약 조건)

반드시 지켜야 할 규칙

- GOV 준수
- STD 준수
- 중복 금지
- 누락 금지

---

## 8. Quality Check (품질 검증)

출력 전 자체 검증

- 정확성
- 완전성
- 일관성
- 재사용성

---

# 제5조 (CMD → PRM 변환 흐름)

```text id="cmd-to-prm"
CMD 입력
    ↓
CMD Parser
    ↓
PRM 생성
    ↓
AI 실행
    ↓
Agent 분해
    ↓
결과 생성
```

---

# 제6조 (PRM 실행 단계)

PRM은 다음 단계로 실행된다.

```text id="prm-flow"
1. 명령 해석
2. 작업 분해
3. Agent 할당
4. 실행
5. 결과 통합
6. 품질 검증
7. 출력
```

---

# 제7조 (Agent 연결 구조)

PRM은 Agent를 직접 생성한다.

예:

```text id="agent-map"
PRM → Planner Agent
PRM → Developer Agent
PRM → Tester Agent
PRM → Reviewer Agent
PRM → Knowledge Agent
```

---

# 제8조 (표준 프롬프트 예시)

## /build 실행 시 PRM

```text id="build-prm"
ROLE: System Architect + Developer

OBJECTIVE:
AutoKnowledge Lite 시스템 전체 생성

CONTEXT:
MDE GOV-001, CMD-001 기준

INPUT:
/build AutoKnowledge-Lite

PROCESS:
1. SDS 분석
2. Architecture 설계
3. Module 분해
4. Code 생성
5. Test 생성

OUTPUT:
- Project Structure
- Source Code
- Test Cases
- Documentation

CONSTRAINTS:
- GOV 준수
- STD 준수
- 누락 금지

QUALITY CHECK:
- 실행 가능성
- 구조 일관성
- 재사용성
```

---

# 제9조 (PRM 표준화 원칙)

- 모든 CMD는 PRM을 통해 실행된다
- PRM은 재사용 가능해야 한다
- PRM은 버전 관리된다
- PRM은 Knowledge로 저장된다

---

# 제10조 (PRM 확장 구조)

향후 PRM은 다음으로 확장된다.

- PRM-002 : 프롬프트 라이브러리
- PRM-003 : 프롬프트 조합 시스템
- PRM-004 : 자동 프롬프트 생성
- PRM-005 : 프롬프트 평가 시스템

---

## PRM-001 자체 검토

✓ CMD → PRM 변환 구조 정의 완료  
✓ 프롬프트 표준 구조 정의 완료  
✓ Agent 연결 구조 정의 완료  
✓ 실행 흐름 정의 완료  
✓ 확장 구조 정의 완료  

**검토 결과 : 이상 없음**