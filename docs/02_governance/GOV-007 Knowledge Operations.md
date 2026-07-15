# 📘 GOV-001
# 제7장 Knowledge 운영 (Knowledge Operations)

---

# 제58조 (목적)

본 장은 MDE(My Development Ecosystem)의 모든 지식 자산을 생성, 저장, 연결, 검색, 재사용 및 개선하기 위한 운영 원칙을 정의한다.

Knowledge는 프로젝트보다 오래 유지되는 핵심 자산으로 관리한다.

---

# 제59조 (Knowledge Platform)

Knowledge Platform은 MDE의 중앙 지식 저장소이다.

다음 구성 요소를 포함한다.

```text
Knowledge Platform

├── Git Repository
├── Obsidian Vault
├── Prompt Library
├── Template Library
├── Development Log
├── Error Library
├── Project Archive
├── AI Memory Index
└── Search Index
```

모든 프로젝트는 Knowledge Platform과 연결된다.

---

# 제60조 (Knowledge 분류)

Knowledge는 다음과 같이 분류한다.

### Project

- SDS
- Architecture
- API
- UI
- DB

---

### Development

- Source Code
- Library
- Component
- Script

---

### AI

- Prompt
- Agent
- Workflow
- Command

---

### Operation

- Error
- Bug
- Release
- Test

---

### Personal

- Note
- Idea
- Research
- Memo

모든 Knowledge는 하나 이상의 분류를 가진다.

---

# 제61조 (Knowledge 생성)

Knowledge는 다음 상황에서 자동 또는 수동으로 생성한다.

자동 생성

- 프로젝트 생성
- 코드 생성
- 테스트 완료
- Release 완료
- AI 실행 결과

수동 생성

- 회고
- 아이디어
- 기술 조사
- 사용자 메모
- 설계 검토

---

# 제62조 (Knowledge 저장)

모든 Knowledge는 다음 정보를 포함한다.

- Knowledge ID
- 제목
- 분류
- 작성일
- 작성자
- 관련 프로젝트
- 관련 문서
- 버전
- 태그
- 상태

Knowledge는 Markdown 형식을 기본으로 한다.

---

# 제63조 (Knowledge 연결)

Knowledge는 상호 연결을 기본 원칙으로 한다.

예시

```text
SDS
 ↓
Architecture
 ↓
Database
 ↓
API
 ↓
Source Code
 ↓
Test
 ↓
Release
 ↓
Retrospective
```

모든 문서는 관련 Knowledge와 링크를 유지한다.

---

# 제64조 (Knowledge 검색)

Knowledge Platform은 다음 기준으로 검색을 지원한다.

- 제목
- 태그
- 프로젝트
- 문서 번호
- Agent
- Prompt
- 날짜
- 버전
- 키워드

검색 결과는 관련 Knowledge를 함께 제안한다.

---

# 제65조 (Knowledge 재사용)

새 프로젝트는 반드시 기존 Knowledge를 먼저 검색한다.

재사용 우선순위

1. Template
2. Prompt
3. Source Code
4. Architecture
5. Workflow
6. Error Solution

재사용 시 원본과의 연결 관계를 유지한다.

---

# 제66조 (Knowledge 품질)

Knowledge는 다음 기준으로 관리한다.

□ 최신 상태

□ 정확성

□ 표준 준수

□ 검색 가능

□ 재사용 가능

□ 연결성 유지

□ 버전 관리

□ 변경 이력 기록

---

# 제67조 (Knowledge 생명주기)

모든 Knowledge는 다음 생명주기를 따른다.

```text
생성(Create)

↓

검토(Review)

↓

승인(Approve)

↓

활용(Use)

↓

개선(Improve)

↓

보관(Archive)
```

오래된 Knowledge도 삭제하지 않고 Archive로 관리한다.

---

# 제68조 (AI Knowledge 활용)

AI는 Knowledge Platform을 우선 활용한다.

AI는 다음 순서로 정보를 찾는다.

1. Knowledge Base
2. Template Library
3. Prompt Library
4. Project Archive
5. Error Library
6. External Source

외부 정보보다 내부 Knowledge를 우선 활용하는 것을 원칙으로 한다.

---

## 제7장 자체 검토

✓ Knowledge Platform 정의 완료

✓ 분류 체계 정의 완료

✓ 저장 기준 정의 완료

✓ 연결 원칙 정의 완료

✓ 검색 및 재사용 원칙 정의 완료

✓ AI 활용 원칙 정의 완료

**검토 결과 : 이상 없음**