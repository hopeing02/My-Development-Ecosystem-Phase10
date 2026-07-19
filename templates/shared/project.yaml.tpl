version: 1
project:
  id: {{PROJECT_NAME}}
  name: {{PROJECT_TITLE}}
repository:
  default_branch: main
  branch_pattern: "{type}/{assignee}/{task_id}"
  protected_branches:
    - main
commands:
  test:
    - "uv run pytest"
  build:
    - "uv build"
pull_request:
  required: true
  approvals_required: 1
  require_tests: true
