# 📘 SDS-001
# AutoKnowledge Lite Project Design Specification

---

# 제1조 (문서 목적)

본 문서는 MDE(My Development Ecosystem) 기반에서 AutoKnowledge Lite 시스템을 설계하기 위한 공식 프로젝트 설계서이다.

이 문서는 CMD, PRM, GOV 표준을 기반으로 실제 구현 가능한 시스템 구조를 정의한다.

---

# 제2조 (프로젝트 개요)

## 2.1 프로젝트 명

AutoKnowledge Lite

---

## 2.2 프로젝트 목적

사용자가 모바일에서 공유한 콘텐츠를 기반으로:

- AI 요약
- Markdown 변환
- 자동 정리
- Obsidian 저장
- GitHub 업로드

까지 자동 수행하는 지식 자동화 시스템 구축

---

## 2.3 핵심 가치

- Zero Manual Note Taking
- AI-based Knowledge Structuring
- Instant Markdown Generation
- Git-based Knowledge Versioning

---

# 제3조 (해결하려는 문제)

현재 문제:

- 정보 저장이 수동적임
- 메모가 분산됨
- Obsidian 입력 번거로움
- Git 기록 관리 어려움
- AI 활용 흐름 단절

---

# 제4조 (해결 방식)

AutoKnowledge Lite는 다음 흐름으로 해결한다.

```text id="flow-main"
Android Share
    ↓
AI Processing
    ↓
Summary Generation
    ↓
Markdown Creation
    ↓
Auto Tagging
    ↓
Obsidian Save
    ↓
GitHub Sync
```

---

# 제5조 (시스템 구조)

## 5.1 전체 구조

```text id="system-structure"
AutoKnowledge Lite
├── Mobile Share Handler
├── AI Processing Engine
├── Markdown Generator
├── Knowledge Classifier
├── Storage Layer (Obsidian)
└── Sync Layer (GitHub)
```

---

## 5.2 구성 요소 설명

### 1. Share Handler
- Android 공유 이벤트 수신

---

### 2. AI Processing Engine
- GPT/Claude 기반 요약
- 핵심 정보 추출

---

### 3. Markdown Generator
- 표준 PRM 기반 변환
- 구조화된 문서 생성

---

### 4. Knowledge Classifier
- 태그 자동 생성
- 카테고리 분류

---

### 5. Storage Layer
- Obsidian Vault 저장

---

### 6. Sync Layer
- GitHub 자동 push

---

# 제6조 (데이터 흐름)

```text id="data-flow"
Input (Share)
    ↓
Preprocess
    ↓
AI Summary (PRM-001)
    ↓
Structure Mapping
    ↓
Markdown Output
    ↓
Save to Obsidian
    ↓
Git Commit & Push
```

---

# 제7조 (기술 스택)

## 7.1 Frontend / Mobile
- Android Share Intent

## 7.2 Backend
- Google Apps Script / Node.js / Python (선택)

## 7.3 AI Engine
- OpenAI GPT / Claude API

## 7.4 Storage
- Obsidian Vault (Local)
- GitHub Repository

---

# 제8조 (폴더 구조)

```text id="folder-structure"
AutoKnowledge-Lite/
├── src/
│   ├── handler/
│   ├── ai/
│   ├── generator/
│   └── sync/
├── vault/
│   ├── notes/
│   ├── tags/
│   └── index/
├── logs/
├── config/
└── README.md
```

---

# 제9조 (CMD 연동)

본 시스템은 CMD-001 명령과 직접 연결된다.

| CMD | 기능 |
|-----|------|
| /new | 프로젝트 생성 |
| /build | 전체 생성 |
| /doc | 문서 생성 |
| /obsidian | 저장 |
| /git | 업로드 |

---

# 제10조 (PRM 연동)

모든 실행은 PRM-001 기반으로 처리된다.

- Share Input → PRM 변환
- AI Processing → PRM Execution
- Output → PRM Format

---

# 제11조 (출력 포맷)

모든 결과는 Markdown 표준으로 생성된다.

```text id="output-format"
# Title
## Summary
## Key Points
## Tags
## Source
```

---

# 제12조 (자동화 정책)

- 모든 문서는 자동 생성 가능
- 모든 저장은 자동 수행
- 모든 Git 반영은 자동 commit
- 사용자 개입 최소화

---

# 제13조 (확장성)

향후 확장:

- PRM-002 (프롬프트 라이브러리)
- CMD GUI 앱
- AI Agent 분리 시스템
- Multi-user Knowledge Sync
- Cloud 기반 Vault

---

## SDS-001 자체 검토

✓ 시스템 구조 정의 완료  
✓ 데이터 흐름 정의 완료  
✓ 폴더 구조 정의 완료  
✓ CMD/PRM 연동 완료  
✓ 자동화 설계 완료  

**검토 결과 : 이상 없음**