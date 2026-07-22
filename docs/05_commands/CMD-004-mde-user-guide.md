# CMD-004 MDE 전체 사용자 가이드

- 버전: 1.0.0
- 상태: Active
- 작성일: 2026-07-22

## 1. 목적

이 문서는 MDE 전체 CLI의 시작점과 안전한 일상 사용 흐름을 설명한다. 세부 옵션의 기준은 실행 중인 CLI이며, 아래 자동 관리 구간은 `mde docs` 명령으로 동기화한다.

## 2. 실행 준비

Python 3.11 이상과 `uv`를 준비하고 저장소 루트에서 실행한다.

```powershell
cd C:\My-Development-Ecosystem-Phase10
uv run mde --help
```

## 3. 프로젝트 생성

현재 기본 템플릿은 `shared`다.

```powershell
uv run mde new sample-project
uv run mde new sample-project --template shared
```

## 4. 패치 적용

단일 패치는 대상 파일을 명시한다. 기본적으로 적용 후 pytest를 실행하고 백업을 유지한다.

```powershell
uv run mde apply change.patch --target path/to/target.py
uv run mde apply change.patch --target path/to/target.py --no-test
```

Task manifest는 `manifest.yaml` 경로를 전달한다.

```powershell
uv run mde apply tasks/example/manifest.yaml
```

`--remove-backup`은 성공 후 백업을 제거하므로 필요한 경우에만 사용한다.

## 5. 변경 저장

`save`는 포맷, 테스트, Git 커밋과 선택적 push를 수행한다. 커밋 대상과 작업 트리를 먼저 확인한다.

```powershell
git status --short
uv run mde save -m "feat: describe the change" --no-push
```

`--no-push`를 생략하면 원격 push가 수행될 수 있다.

## 6. Workflow

```powershell
uv run mde workflow list
uv run mde workflow show <workflow-name>
uv run mde workflow run <workflow-name> --message "작업 설명"
```

기본 `workflow run`은 안전한 dry run이다. 실제 테스트·Git 플러그인을 사용하려면 `--runtime`을 명시한다.

```powershell
uv run mde workflow run <workflow-name> --runtime
```

## 7. Task

```powershell
uv run mde task list
uv run mde task list --status failed
uv run mde task show <task-id>
uv run mde task run <task-id>
uv run mde task retry <task-id>
uv run mde task checkpoint <task-id>
uv run mde task summary
```

`task run`은 `pending` 상태의 Task만 실행한다.

## 8. Agent

한 번만 실행:

```powershell
uv run mde agent --once
```

지속 감시:

```powershell
uv run mde agent --watch --interval 30
```

`--auto-save`, `--no-push`, `--allow-dirty`는 Git 변경을 수반할 수 있으므로 작업 트리 상태를 확인한 뒤 사용한다.

## 9. Sync

```powershell
uv run mde sync status
uv run mde sync pull
uv run mde sync run --no-commit --no-push
```

`sync pull`은 깨끗한 작업 트리를 요구한다. `sync run`은 옵션에 따라 Task 실행, 커밋, push까지 수행할 수 있다.

## 10. AI Provider

```powershell
uv run mde ai list
uv run mde ai check
uv run mde ai check --provider mock
```

외부 Provider는 해당 환경 변수와 API 키가 필요하다. `mock`은 외부 AI 호출 없이 기본 동작을 확인할 때 사용한다.

## 11. Plugin

```powershell
uv run mde plugin list
```

현재 등록된 Workflow runtime plugin을 확인한다.

## 12. Knowledge

```powershell
uv run mde knowledge list
uv run mde knowledge scan mde-docs
uv run mde knowledge search "검색어" --source mde-docs
```

개인·업무 Source는 기본 민감 정책이 적용된다. 전체 사용법은 `CMD-003-mde-knowledge-plugin-user-guide.md`를 따른다.

## 13. 문서 동기화

현재 문서와 실제 CLI의 차이를 확인한다.

```powershell
uv run mde docs check
```

변경안을 미리 본다. 이 명령은 파일을 수정하지 않는다.

```powershell
uv run mde docs update
```

검토한 변경안을 관리 구간에 적용한다.

```powershell
uv run mde docs update --apply
```

Knowledge Plugin 상세 가이드도 별도 target으로 검사하고 갱신할 수 있다.

```powershell
uv run mde docs check --target knowledge-guide
uv run mde docs update --target knowledge-guide
uv run mde docs update --target knowledge-guide --apply
```

자동 변경 범위는 아래 표식 사이로 제한된다. 설명 본문, 다른 문서, 원본 자료, Git 상태는 변경하지 않는다.

<!-- MDE-DOCS:CLI-REFERENCE:START -->
## 자동 관리 CLI 참조

이 구간은 실제 MDE CLI 정의에서 생성된다. 직접 수정하지 않는다.

| 명령 | 상태 | 설명 |
|---|---|---|
| `mde new` | implemented | Create a new MDE project. |
| `mde generate` | reserved | Generate MDE code artifacts. |
| `mde apply` | implemented | Apply a patch file or task manifest. |
| `mde save` | implemented | Format, test, commit, and optionally push changes. |
| `mde agent` | implemented | Run the MDE mobile automation agent. |
| `mde workflow` | implemented | Inspect and run YAML workflows. |
| `mde task` | implemented | Inspect and execute YAML tasks. |
| `mde sync` | implemented | Synchronize mobile tasks through GitHub. |
| `mde ai` | implemented | Inspect configured AI providers. |
| `mde plugin` | implemented | Inspect installed workflow plugins. |
| `mde inbox` | reserved | Manage legacy inbox patch files. |
| `mde knowledge` | implemented | Manage local Markdown knowledge sources and indexes. |
| `mde docs` | implemented | Check and safely update managed MDE documentation. |
| `mde build` | reserved | Reserved command: build |
| `mde release` | reserved | Reserved command: release |
| `mde obsidian` | reserved | Reserved command: obsidian |
| `mde deploy` | reserved | Reserved command: deploy |

### `mde new`

- `mde new [-h] [--template TEMPLATE] project_name`

### `mde apply`

- `mde apply [-h] [--target TARGET] [--no-test] [--remove-backup] source`

### `mde save`

- `mde save [-h] -m MESSAGE [--no-push]`

### `mde agent`

- `mde agent [-h] [--once | --watch] [--interval INTERVAL] [--auto-save] [--no-push] [--allow-dirty]`

### `mde workflow`

- `mde workflow list [-h]`
- `mde workflow show [-h] workflow_name`
- `mde workflow run [-h] [--message MESSAGE] [--task TASK_ID] [--runtime] workflow_name`

### `mde task`

- `mde task list [-h] [--status {pending,processing,completed,failed}]`
- `mde task show [-h] task_id`
- `mde task run [-h] task_id`
- `mde task retry [-h] task_id`
- `mde task checkpoint [-h] task_id`
- `mde task summary [-h]`

### `mde sync`

- `mde sync status [-h]`
- `mde sync pull [-h]`
- `mde sync run [-h] [--no-commit] [--no-push] [--allow-dirty] [--remote REMOTE] [--branch BRANCH] [--task-branches]`

### `mde ai`

- `mde ai list [-h]`
- `mde ai check [-h] [--provider PROVIDER]`

### `mde plugin`

- `mde plugin list [-h]`

### `mde knowledge`

- `mde knowledge add [-h] --name NAME --category {development,project,personal,work,shared} [--type {markdown,obsidian}] path`
- `mde knowledge list [-h]`
- `mde knowledge show [-h] source`
- `mde knowledge update [-h] [--enabled ENABLED] [--agent-access AGENT_ACCESS] [--confirm-sensitive-access] source`
- `mde knowledge remove [-h] source`
- `mde knowledge scan [-h] [--all] [--category {development,project,personal,work,shared}] [--include-sensitive] [source]`
- `mde knowledge search [-h] [--source SOURCE] [--category {development,project,personal,work,shared}] [--tag TAG] [--limit LIMIT] [--all] [--include-sensitive] [query]`
- `mde knowledge backlinks [-h] --source SOURCE [--limit LIMIT] document`

### `mde docs`

- `mde docs check [-h] [--target {mde-user-guide,knowledge-guide}]`
- `mde docs update [-h] [--target {mde-user-guide,knowledge-guide}] [--apply]`
<!-- MDE-DOCS:CLI-REFERENCE:END -->

## 14. 예약 명령

CLI 목록에 `reserved`로 표시되는 명령은 이름만 예약되어 있고 아직 실행 기능이 없다. 예약 명령 실행은 상태 코드 2를 반환하며, 구현된 기능으로 간주하지 않는다.

## 15. 권장 일상 흐름

```text
작업 트리 확인
→ 필요한 MDE 명령 실행
→ 테스트
→ mde docs check
→ Knowledge 문서 변경 시 mde knowledge scan mde-docs
→ 변경 범위 재확인
→ mde save 또는 명시적 Git 커밋
```

문서 자동 갱신은 자동 커밋이나 push를 수행하지 않는다.

## 16. 문제 해결

전체 도움말:

```powershell
uv run mde --help
uv run mde <command> --help
```

`uv` 캐시 경로에 문제가 있으면 쓰기 가능한 별도 캐시를 현재 세션에 지정할 수 있다.

```powershell
$env:UV_CACHE_DIR = Join-Path $env:TEMP "mde-uv-cache"
uv run mde --help
```
