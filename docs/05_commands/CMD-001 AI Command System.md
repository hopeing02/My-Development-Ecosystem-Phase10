# 📘 CMD-001
# AI Command System (명령 체계)

---

# 제1조 (목적)

본 문서는 MDE(My Development Ecosystem)에서 사용자가 AI 시스템을 직접 제어하기 위한 표준 명령어 체계를 정의한다.

CMD는 모든 자동화, 생성, 실행, 배포의 **유일한 사용자 인터페이스 계층(UI Layer)** 이다.

---

# 제2조 (CMD의 역할)

CMD는 다음 역할을 수행한다.

- AI 작업 트리거
- Workflow 실행 시작점
- 자동화 시스템 제어
- 프로젝트 생성 및 관리
- Knowledge 생성 트리거

---

# 제3조 (CMD 구조)

모든 명령은 다음 구조를 따른다.

```text id="cmd-structure"
/command [target] [options]
```

예:
- `/new AutoKnowledge-Lite`
- `/build SDS-001`
- `/doc GOV-001`
- `/git push`

---

# 제4조 (표준 명령 목록)

## 1. 프로젝트 생성

### /new
새 프로젝트 생성

```text id="cmd-new"
/new [project-name]
```

예:
- `/new AutoKnowledge-Lite`

---

## 2. 설계 생성

### /sds
SDS 생성

```text id="cmd-sds"
/sds [project-name]
```

---

### /design
시스템 설계 생성

```text id="cmd-design"
/design [module]
```

---

## 3. 개발

### /code
코드 생성

```text id="cmd-code"
/code [module]
```

---

### /build
전체 빌드 실행

```text id="cmd-build"
/build [project]
```

---

## 4. 문서 생성

### /doc
문서 생성

```text id="cmd-doc"
/doc [document-id]
```

---

### /ui
UI 설계 생성

```text id="cmd-ui"
/ui [feature]
```

---

## 5. 테스트

### /test
테스트 생성 및 실행

```text id="cmd-test"
/test [module]
```

---

## 6. Git 연동

### /git
Git 작업 수행

```text id="cmd-git"
/git [action]
```

예:
- `/git commit`
- `/git push`
- `/git sync`

---

## 7. Obsidian 연동

### /obsidian
Obsidian 저장

```text id="cmd-obsidian"
/obsidian [note]
```

---

## 8. 릴리스

### /release
릴리스 수행

```text id="cmd-release"
/release [version]
```

---

## 9. 품질 및 개선

### /review
코드/문서 리뷰

```text id="cmd-review"
/review [target]
```

---

### /fix
문제 수정

```text id="cmd-fix"
/fix [issue]
```

---

### /optimize
최적화

```text id="cmd-optimize"
/optimize [target]
```

---

## 10. 보고 및 기록

### /report
상태 보고

```text id="cmd-report"
/report [project]
```

---

# 제5조 (CMD 실행 흐름)

모든 명령은 다음 흐름을 따른다.

```text id="cmd-flow"
User Command 입력
    ↓
CMD Parser
    ↓
GOV 규칙 검증
    ↓
PRM 프롬프트 생성
    ↓
AI 실행
    ↓
Agent 처리
    ↓
결과 생성
    ↓
Git / Obsidian / KB 저장
```

---

# 제6조 (CMD 권한 구조)

| 레벨 | 설명 |
|------|------|
| L1 | 조회 명령 |
| L2 | 생성 명령 |
| L3 | 실행 명령 |
| L4 | 시스템 변경 명령 |

---

## 제한 규칙

- CON 변경 ❌
- GOV 변경 ❌
- 시스템 구조 변경 ❌ (CMD로 직접 불가)

---

# 제7조 (CMD + PRM 연동)

CMD는 직접 실행하지 않는다.

항상 다음을 거친다:

```text id="cmd-prm"
CMD → PRM → AI → Agent → Output
```

즉 CMD는 “명령”, PRM은 “실행 설계”이다.

---

# 제8조 (자동화 연동)

CMD는 자동화 시스템과 직접 연결된다.

예:

- `/new` → SDS + Architecture 자동 생성
- `/build` → 코드 + 테스트 자동 생성
- `/release` → Git + Obsidian + KB 자동 반영

---

# 제9조 (확장 원칙)

CMD는 다음 원칙으로 확장된다.

- 짧고 직관적일 것
- 기능 중복 금지
- AI 실행 가능해야 함
- Workflow와 연결되어야 함

---

# 제10조 (표준 명령 철학)

CMD는 단순 명령어가 아니다.

> “사용자가 AI 시스템 전체를 제어하는 언어”

---

## CMD-001 자체 검토

✓ 명령 구조 정의 완료  
✓ 표준 명령 정의 완료  
✓ 실행 흐름 정의 완료  
✓ 권한 구조 정의 완료  
✓ 자동화 연동 정의 완료  

**검토 결과 : 이상 없음**