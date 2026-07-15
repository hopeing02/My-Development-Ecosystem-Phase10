# 📘 CON-000
# 제10장 문서 체계 (Documentation System)

---

## 제61조 (문서 체계의 목적)

MDE는 모든 프로젝트를 문서 중심(Document-Driven Development)으로 관리한다.

문서는 단순한 기록이 아니라 프로젝트의 설계, 개발, 운영 및 지식 관리의 기준이 된다.

모든 프로젝트는 본 문서 체계를 따른다.

---

# 제62조 (문서 계층)

MDE 문서는 다음 계층으로 구성한다.

```text
Level 0 : Constitution
Level 1 : Governance
Level 2 : Standards
Level 3 : Architecture
Level 4 : Platform
Level 5 : Project
Level 6 : Knowledge
Level 7 : Archive
```

상위 문서는 하위 문서의 기준이 되며, 하위 문서는 상위 문서를 위반할 수 없다.

---

# 제63조 (문서 번호 체계)

모든 문서는 다음 형식을 따른다.

```
[분류]-[번호]

예)

CON-000
STD-001
DEV-003
SDS-015
ARC-002
PRM-005
CMD-001
CHK-003
```

번호는 중복되지 않아야 하며, 영구적으로 유지한다.

---

# 제64조 (문서 분류)

MDE는 다음 문서 유형을 정의한다.

| 코드 | 문서명 | 목적 |
|------|--------|------|
| CON | Constitution | 최상위 헌법 |
| GOV | Governance | 운영 정책 |
| STD | Standard | 공통 표준 |
| DEV | Development | 개발 표준 |
| ARC | Architecture | 시스템 설계 |
| AGT | Agent | AI Agent 설계 |
| WFL | Workflow | 업무 흐름 |
| PRM | Prompt | 프롬프트 표준 |
| CMD | Command | AI 명령 체계 |
| CHK | Checklist | 품질 검수 |
| SDS | Software Design Specification | 프로젝트 설계 |
| PMO | Project Management | 프로젝트 운영 |
| AUTO | Automation | 자동화 설계 |
| TMP | Template | 템플릿 |
| API | API Specification | API 명세 |
| DB | Database | 데이터 설계 |
| UI | User Interface | 화면 설계 |
| KB | Knowledge Base | 지식 문서 |
| REL | Release | 릴리스 관리 |
| LOG | Development Log | 개발 일지 |

---

# 제65조 (문서 구성 표준)

모든 문서는 최소한 다음 항목을 포함한다.

- 문서 번호
- 문서명
- 버전
- 상태(Draft, Review, Approved)
- 작성일
- 작성자
- 변경 이력
- 목적
- 본문
- 자체 검토 결과

---

# 제66조 (문서 생명주기)

모든 문서는 다음 생명주기를 따른다.

```text
초안(Draft)

↓

검토(Review)

↓

승인(Approved)

↓

운영(Active)

↓

개정(Revised)

↓

보관(Archived)
```

각 단계의 변경 사항은 변경 이력에 기록한다.

---

# 제67조 (문서 연결 원칙)

문서는 독립적으로 존재하지 않는다.

관련 문서를 상호 참조하여 연결한다.

예시

- CON → STD
- STD → DEV
- DEV → SDS
- SDS → API
- API → CODE
- CODE → TEST
- TEST → REL
- REL → KB

이를 통해 프로젝트 전체의 추적성을 확보한다.

---

# 제68조 (문서 저장소)

문서는 다음 저장소에 관리한다.

### Git Repository

- 버전 관리
- 변경 이력
- 협업

### Obsidian Vault

- 지식 연결
- 백링크
- 그래프
- 검색

### AutoKnowledge Lite

- AI 검색
- 자동 요약
- 문서 추천
- 재사용 자산 관리

세 저장소는 동일한 문서를 기준으로 연동한다.

---

# 제69조 (문서 품질 기준)

모든 문서는 다음 기준을 만족해야 한다.

□ 번호 체계 준수

□ 최신 버전 유지

□ 변경 이력 작성

□ 상위 문서와 일관성 유지

□ 관련 문서 연결

□ 검색 가능

□ AI 활용 가능

□ 재사용 가능

---

# 제70조 (문서 체계의 목적)

MDE 문서 체계의 최종 목적은 다음과 같다.

- 문서를 프로젝트의 중심 자산으로 관리한다.
- AI가 문서를 이해하고 활용할 수 있도록 구조화한다.
- 프로젝트가 종료되어도 지식이 지속적으로 활용되도록 한다.
- 모든 프로젝트가 동일한 방식으로 운영되도록 한다.

---

## 제10장 자체 검토

✓ 문서 계층 정의 완료

✓ 문서 번호 체계 정의 완료

✓ 문서 분류 정의 완료

✓ 문서 생명주기 정의 완료

✓ 문서 품질 기준 정의 완료

✓ 저장소 연계 원칙 정의 완료

**검토 결과 : 이상 없음**
