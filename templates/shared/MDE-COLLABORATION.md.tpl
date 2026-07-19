# {{PROJECT_TITLE}} 협업 설정

## GitHub 저장소 변수

- `MDE_CORE_REPOSITORY`: `owner/mde-core` 형식의 MDE Core 저장소
- `MDE_CORE_REF`: 팀에서 승인한 태그 또는 commit SHA

## GitHub Ruleset

`main` 브랜치에 다음 규칙을 적용한다.

1. Pull Request 없이 변경 금지
2. 승인 1명 이상 요구
3. 새 commit이 추가되면 기존 승인 무효화
4. `verify` 상태 검사 통과 요구
5. branch 삭제와 force push 금지
6. 관리자 우회는 비상 운영자에게만 허용

## 작업 규칙

- 작업 YAML의 `assignee`에는 GitHub 사용자명을 기록한다.
- 브랜치는 `<type>/<assignee>/<task-id>`로 생성한다.
- `mde test`와 `mde build` 성공 후 Pull Request를 생성한다.

```yaml
version: 1
task:
  id: TASK-001
  type: feature
  title: 작업 제목
  assignee: github-user
  workflow: feature
  repository:
    base_branch: main
    branch: feature/github-user/task-001
```
