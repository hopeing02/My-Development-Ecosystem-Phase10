# 📘 GOV-001
# 제5장 프로젝트 운영 (Project Operations)

---

# 제37조 (목적)

본 장은 MDE(My Development Ecosystem)의 모든 프로젝트가 동일한 절차와 기준에 따라 생성, 개발, 운영 및 종료되도록 하는 표준 운영 체계를 정의한다.

모든 프로젝트는 문서 중심(Document-Driven Development)과 AI 협업(AI-Assisted Development)을 원칙으로 한다.

---

# 제38조 (프로젝트 생명주기)

모든 프로젝트는 다음 생명주기를 따른다.

```text
아이디어(Idea)
    ↓
프로젝트 생성(Create)
    ↓
기획(Planning)
    ↓
설계(Design)
    ↓
개발(Development)
    ↓
테스트(Test)
    ↓
배포(Release)
    ↓
운영(Operation)
    ↓
회고(Retrospective)
    ↓
Knowledge 등록
```

각 단계의 산출물은 다음 단계의 입력으로 사용한다.

---

# 제39조 (프로젝트 생성)

새 프로젝트는 `/new` 명령 또는 Project Wizard를 통해 생성한다.

생성 시 자동으로 다음 항목을 준비한다.

- 프로젝트 ID
- 프로젝트 폴더
- Git 저장소 연결
- Obsidian 프로젝트 노트 생성
- 기본 README
- CHANGELOG
- LICENSE
- 표준 폴더 구조
- 기본 템플릿

---

# 제40조 (프로젝트 계획)

Planning 단계에서는 다음 문서를 작성한다.

필수 문서

- 프로젝트 개요
- 요구사항 정의
- 일정 계획
- 범위 정의
- 위험 요소 분석

산출물

- SDS 초안
- Project Roadmap
- 작업 목록(Backlog)

---

# 제41조 (프로젝트 설계)

Design 단계에서는 다음 항목을 설계한다.

- Architecture
- Database
- API
- UI/UX
- Workflow
- AI Agent 구성
- Prompt 전략

설계 변경은 변경 관리 절차를 따른다.

---

# 제42조 (프로젝트 개발)

Development 단계에서는 다음 원칙을 적용한다.

- DEV 표준 준수
- 코드 리뷰 수행
- 테스트 코드 작성
- 문서 동기화
- Commit 규칙 준수

모든 개발 결과는 Git으로 관리한다.

---

# 제43조 (프로젝트 테스트)

테스트는 다음 순서로 수행한다.

1. Unit Test
2. Integration Test
3. System Test
4. User Acceptance Test(UAT)

테스트 결과는 프로젝트 문서에 기록한다.

---

# 제44조 (프로젝트 릴리스)

릴리스 전 확인 사항

□ 기능 완료

□ 테스트 통과

□ 문서 최신화

□ CHANGELOG 작성

□ 버전 업데이트

□ Release Note 작성

□ Knowledge 등록 준비

릴리스는 User 승인 후 수행한다.

---

# 제45조 (프로젝트 운영)

운영 단계에서는 다음 항목을 관리한다.

- 버그 수정
- 성능 개선
- 사용자 피드백
- 기능 개선
- 보안 업데이트
- 문서 유지

운영 결과는 다음 버전에 반영한다.

---

# 제46조 (프로젝트 회고)

프로젝트 종료 후 반드시 회고를 수행한다.

회고 내용

- 잘된 점
- 개선할 점
- 발생한 문제
- 해결 방법
- AI 활용 결과
- 재사용 가능한 자산

회고 결과는 Knowledge Platform에 등록한다.

---

# 제47조 (프로젝트 종료)

프로젝트 종료 시 다음을 완료한다.

- 최종 문서 정리
- Git Tag 생성
- Release Archive 작성
- Knowledge 등록
- 템플릿 추출
- 재사용 코드 분리

프로젝트 종료는 개발의 끝이 아니라 Knowledge의 시작으로 본다.

---

## 제5장 자체 검토

✓ 프로젝트 생명주기 정의 완료

✓ 프로젝트 생성 절차 정의 완료

✓ 기획·설계·개발·테스트·릴리스 절차 정의 완료

✓ 회고 및 Knowledge 등록 절차 정의 완료

**검토 결과 : 이상 없음**