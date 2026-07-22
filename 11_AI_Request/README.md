# 11_AI_Request

Codex, Claude Code, Gemini에 전달하는 실제 AI 요청서를 관리한다.

## 파일명

```text
YYYY-MM-DD-<provider>-<request-id>.md
```

`provider`는 `codex`, `claude-code`, `gemini` 중 하나를 사용한다.

## 필수 항목

- 요청 ID
- 작성일
- 대상 AI
- 목적
- 요청 내용
- 제약 조건
- 기대 결과
- 처리 상태

공급자별 기본 양식은 `templates/`에서 복사해 사용한다. 상세 규칙은 `docs/03_standards/STD-001-development-record-management.md`를 따른다.
