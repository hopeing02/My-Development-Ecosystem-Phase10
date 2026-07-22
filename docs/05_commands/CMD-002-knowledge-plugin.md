# CMD-002 Knowledge Plugin CLI

- 버전: 1.0.0
- 상태: Active
- 작성일: 2026-07-22

## 명령

```text
mde knowledge add <path> --name <name> --category <category> [--type markdown|obsidian]
mde knowledge list
mde knowledge show <name-or-id>
mde knowledge update <name-or-id> [--enabled true|false] [--agent-access true|false]
mde knowledge remove <name-or-id>
mde knowledge scan <name-or-id>
mde knowledge scan --all [--include-sensitive]
mde knowledge scan --category <category> [--include-sensitive]
mde knowledge search [query] [--source <source>] [--category <category>] [--tag <tag>]
mde knowledge backlinks <document> --source <source>
```

민감 Source의 Agent 접근 활성화에는 `--confirm-sensitive-access`가 필요하다. Source를 지정하지 않은 검색과 `scan --all`은 personal 및 work를 제외한다.

## 자체 검토

v1에서 허용된 명령만 등록했으며 ask, sync, upload, edit, watch 명령은 추가하지 않았다.
