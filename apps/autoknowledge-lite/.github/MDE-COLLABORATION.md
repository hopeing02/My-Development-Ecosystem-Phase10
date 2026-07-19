# AutoKnowledge Lite 협업 설정

## 저장소 변수

- `MDE_CORE_REPOSITORY`: MDE Core 저장소의 `owner/repository`
- `MDE_CORE_REF`: 팀에서 승인한 MDE Core 태그 또는 commit SHA

## main Ruleset

1. Pull Request 없이 변경 금지
2. 승인 1명 이상 요구
3. 새 commit이 추가되면 기존 승인 무효화
4. `verify` 상태 검사 통과 요구
5. branch 삭제와 force push 금지
6. 관리자 우회는 비상 운영자에게만 허용

작업 브랜치는 `<type>/<assignee>/<task-id>` 형식을 사용한다.
