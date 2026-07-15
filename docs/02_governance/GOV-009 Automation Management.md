# 📘 GOV-001
# 제9장 자동화 관리 (Automation Management)

---

# 제80조 (목적)

본 장은 MDE(My Development Ecosystem)에서 반복되는 모든 작업을 자동화하여, 인간의 개입 없이도 프로젝트 생성, 문서 작성, 코드 관리, 지식 저장이 가능하도록 하는 체계를 정의한다.

자동화는 단순 편의 기능이 아니라 **시스템의 실행 엔진(Execution Engine)** 이다.

---

# 제81조 (자동화 대상)

다음 작업은 자동화 대상이다.

- 프로젝트 생성 (/new)
- 문서 생성 (/doc, /sds)
- 코드 생성 (/code)
- 테스트 생성 (/test)
- Git commit & push (/git)
- Obsidian 저장 (/obsidian)
- 릴리스 (/release)
- Knowledge 등록
- 오류 로그 기록
- Prompt 생성 및 저장
- Workflow 실행

---

# 제82조 (자동화 계층 구조)

자동화는 4단계 구조로 운영한다.

```text id="auto-layer"
Command Layer (/new, /build, /doc)
        ↓
Workflow Layer (SDS → Code → Test)
        ↓
Execution Layer (AI / Agent 실행)
        ↓
Integration Layer (Git / Obsidian / KB)
```

---

# 제83조 (자동화 트리거)

자동화는 다음 상황에서 실행된다.

### 1. 명령 기반 트리거

사용자 입력

- /new
- /build
- /release
- /doc

---

### 2. 이벤트 기반 트리거

- 파일 생성
- 코드 변경
- 테스트 실패
- 릴리스 완료

---

### 3. AI 내부 트리거

- 품질 부족 감지
- 누락 감지
- 구조 오류 감지
- 개선 필요 판단

---

# 제84조 (표준 자동화 흐름)

모든 프로젝트는 다음 자동 흐름을 따른다.

```text id="auto-flow"
/new
  ↓
STD 적용
  ↓
SDS 생성
  ↓
Architecture 설계
  ↓
Prompt 생성
  ↓
Code 생성
  ↓
Test 생성
  ↓
Git Commit
  ↓
Obsidian 저장
  ↓
Knowledge 등록
  ↓
Release
```

---

# 제85조 (Git 자동화)

Git 작업은 자동화 가능해야 한다.

자동 수행 항목:

- commit 생성
- 메시지 자동 생성
- branch 생성
- push 실행
- tag 생성

예:

```text id="git-auto"
auto: sds created
auto: code generated
auto: test passed
auto: release v1.0.0
```

---

# 제86조 (Obsidian 자동화)

Obsidian Vault는 자동 동기화 대상이다.

자동 작업:

- Markdown 생성
- 링크 연결
- 백링크 생성
- 폴더 분류
- 태그 자동 생성

---

# 제87조 (AI 자동 실행 규칙)

AI는 다음 조건에서 자동 실행할 수 있다.

- 명령이 명확할 때
- 표준이 정의되어 있을 때
- 위험도가 낮을 때
- 사용자 승인 범위 내일 때

단, 다음은 반드시 승인 필요:

- CON 변경
- GOV 변경
- 구조 변경
- 릴리스 확정

---

# 제88조 (자동화 안전 장치)

자동화 시스템은 다음 안전장치를 가진다.

### 1. Dry Run 모드
실행 전 시뮬레이션 수행

---

### 2. Rollback 기능
이전 상태로 복원 가능

---

### 3. 로그 기록
모든 자동 작업 기록

---

### 4. 승인 레벨
고위험 작업은 User 승인 필수

---

# 제89조 (자동화 품질 관리)

자동화 결과도 품질 검사를 받는다.

검사 항목:

- 실행 성공 여부
- 데이터 누락 여부
- 구조 일관성
- Git 정상 반영 여부
- Knowledge 등록 여부

---

# 제90조 (자동화 확장 원칙)

자동화는 다음 방향으로 확장한다.

- 수동 작업 제거
- 반복 작업 제거
- AI 실행 비율 증가
- Workflow 표준화
- Agent 기반 실행 확대

---

## 제9장 자체 검토

✓ 자동화 대상 정의 완료

✓ 자동화 계층 구조 정의 완료

✓ 트리거 정의 완료

✓ Git / Obsidian 자동화 정의 완료

✓ 안전장치 정의 완료

✓ 실행 흐름 정의 완료

**검토 결과 : 이상 없음**