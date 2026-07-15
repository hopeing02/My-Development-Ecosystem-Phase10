# 📘 GOV-001
# 제2장 조직 구조 (Organization Structure)

---

# 제8조 (조직 구조)

My Development Ecosystem(MDE)는 사람과 AI가 협력하는 **Hybrid Organization**으로 운영한다.

조직은 다음과 같은 계층 구조를 가진다.

```text
                    User
                     │
             Governance Board
                     │
            ┌────────┴────────┐
            │                 │
      Human Decision     AI Organization
                                │
                         Agent Manager
                                │
        ┌──────────┬──────────┬──────────┐
        │          │          │
   Planning     Development   Knowledge
        │          │          │
      Agents     Agents      Agents
```

사용자는 전략과 최종 의사결정을 담당하며, AI 조직은 실행을 지원한다.

---

# 제9조 (최고 의사결정자)

최고 의사결정자는 사용자(User)이다.

사용자의 책임은 다음과 같다.

- 프로젝트 목표 결정
- 우선순위 결정
- 최종 승인
- 정책 변경 승인
- 릴리스 승인
- AI 활용 범위 결정

AI는 사용자의 결정을 지원하지만 이를 대체하지 않는다.

---

# 제10조 (Governance Board)

Governance Board는 MDE 전체의 운영 정책을 관리한다.

주요 역할

- Framework 관리
- 표준 관리
- 문서 관리
- 품질 관리
- 변경 승인
- 장기 로드맵 관리

개인 프로젝트에서는 사용자가 Governance Board의 역할을 수행하며, 향후 다수의 참여자가 있는 환경에서는 별도의 운영 조직으로 확장할 수 있다.

---

# 제11조 (AI Organization)

AI Organization은 역할 기반의 전문 Agent들로 구성한다.

AI는 하나의 모델이 아니라 여러 전문 Agent가 협업하는 구조를 기본으로 한다.

모든 Agent는 Agent Manager의 관리 아래에서 동작한다.

---

# 제12조 (Agent Manager)

Agent Manager는 AI 조직의 중앙 관리자이다.

주요 책임

- Agent 선택
- 작업 분배
- Workflow 실행
- 결과 통합
- 품질 확인
- 사용자에게 결과 전달

Agent 간 충돌이 발생하면 Agent Manager가 조정한다.

---

# 제13조 (Planning Division)

Planning Division은 프로젝트 기획을 담당한다.

구성 Agent

- Business Analyst Agent
- Requirement Agent
- Planner Agent
- Scheduler Agent

주요 산출물

- 요구사항
- 프로젝트 계획
- 일정
- 우선순위

---

# 제14조 (Development Division)

Development Division은 설계와 구현을 담당한다.

구성 Agent

- Architect Agent
- Database Agent
- API Agent
- UI Agent
- Developer Agent
- Reviewer Agent
- Tester Agent

주요 산출물

- Architecture
- Database
- API
- UI
- Source Code
- Test Code

---

# 제15조 (Knowledge Division)

Knowledge Division은 프로젝트의 모든 지식을 관리한다.

구성 Agent

- Documentation Agent
- Knowledge Manager Agent
- Prompt Manager Agent
- Template Manager Agent

주요 산출물

- 문서
- Knowledge Base
- Prompt Library
- Template Library
- Development Log

---

# 제16조 (Automation Division)

Automation Division은 반복 작업을 자동화한다.

구성 Agent

- Workflow Agent
- Automation Agent
- Git Agent
- Release Agent
- Obsidian Agent

주요 기능

- 프로젝트 생성
- Git 반영
- Markdown 생성
- 릴리스 준비
- Obsidian 동기화

---

# 제17조 (조직 운영 원칙)

모든 조직은 다음 원칙을 따른다.

1. 역할 분리
2. 명확한 책임
3. 표준 준수
4. 문서 기반 운영
5. Workflow 기반 협업
6. Knowledge 공유
7. 지속적 개선

---

## 자체 검토

✓ 조직 구조 정의 완료

✓ Governance Board 정의 완료

✓ AI Organization 정의 완료

✓ Division 구조 정의 완료

✓ Agent Manager 정의 완료

**검토 결과 : 이상 없음**