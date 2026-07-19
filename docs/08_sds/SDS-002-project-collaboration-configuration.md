# SDS-002 프로젝트 협업 설정 상세설계

## 1. 프로젝트 설정

경로는 저장소 루트의 `.mde/project.yaml`이다.

```yaml
version: 1
project:
  id: autoknowledge-lite
  name: AutoKnowledge Lite
repository:
  default_branch: main
  branch_pattern: "{type}/{assignee}/{task_id}"
  protected_branches:
    - main
commands:
  test:
    - ".\\gradlew.bat testDebugUnitTest"
  build:
    - ".\\gradlew.bat assembleDebug"
pull_request:
  required: true
  approvals_required: 1
  require_tests: true
```

필수 필드는 `version`, `project.id`, `project.name`, `repository.default_branch`, `commands.test`, `commands.build`이다. 명령 목록은 비어 있을 수 있지만 목록 타입이어야 한다.

## 2. 작업 설정 확장

```yaml
version: 1
task:
  id: AKL-101
  type: feature
  title: 검색 필터 추가
  assignee: github-user-a
  workflow: feature
  repository:
    base_branch: main
    branch: feature/github-user-a/AKL-101
```

`assignee`는 비어 있지 않은 문자열이며 `/`, 공백, 경로 이동 문자를 포함할 수 없다.

## 3. 검증 오류

- 설정 파일 부재: 프로젝트 설정 필요 명령에서 오류
- 잘못된 YAML 또는 타입: 필드 경로를 포함한 검증 오류
- 보호 브랜치에서 저장 또는 push 시도: 실행 전 오류
- 작업 브랜치 불일치: 기대 브랜치와 실제 브랜치를 함께 표시
- 테스트 또는 빌드 실패: 종료 코드와 실패한 명령을 표시

## 4. 호환성

기존 작업에서 `assignee`가 없는 경우 조회는 가능하지만 실행은 거부한다. 기존 `.mde-project.json`은 새 프로젝트 설정으로 수동 이전한다.
