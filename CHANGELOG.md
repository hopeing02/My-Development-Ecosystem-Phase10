# Changelog

모든 주요 변경 사항을 기록합니다.

## Unreleased

- Fixed automatic repair returning completed before remaining workflow steps ran. Successful retests now resume the original workflow with its policies and checkpoint intact; downstream failures remain failures. Added an acceptance test using real pytest, artifact application, commit, and push to a temporary bare remote with a deterministic AI provider.

- Clarified that generate/inbox and their parsed subcommands remain reserved. Preserved exit code 2 and no-write behavior, synchronized both managed CLI guides, and added regression checks for help and documentation drift.

- Replaced three deprecated Capture HTTP status aliases without changing 413/422 responses. Added httpx2 only to test dependencies for Starlette TestClient compatibility and made Starlette deprecations fail tests. Both Python suites now pass without warnings.

- Stopped tracking six generated mde_core.egg-info files under the existing ADR-010 policy while retaining local copies. Added a regression check and verified that both installation paths leave the Git worktree unchanged.

- Declared and locked Black 26.10.1 for the existing save validation workflow.
- Aligned the mde-core package and AutoKnowledge Lite lock metadata with runtime 0.10.0 and added regression checks for both installation paths.
- Restored the Black formatting baseline across 67 existing Python files without changing their AST or comment text. Full Black, Ruff, Python regression, and lock consistency checks passed; see CODE-008 and TEST-014.

- Added automatic Obsidian aliases, normalized tags, MOC links, graph settings, templates, and Bases for the personal Vault.

- Added AutoKnowledge Lite 0.2.1 PC clipboard and fixed-folder capture page at `/pc`.

- Added a fixed, Tailscale-accessible AutoKnowledge Lite Android APK download endpoint.

- Added AutoKnowledge Lite 0.2.0 fixed Vault folder selection with server-side path allowlisting and Android selection persistence.

- Integrated the complete AutoKnowledge Lite Python and Android implementation into `apps/autoknowledge-lite/` while preserving the personal Vault and Git synchronization settings.

- Excluded local agent workspaces, generated dependencies, runtime data, Android build state, and the preserved nested Vault recovery copy from Git.

- Prevented Knowledge CLI Unicode output crashes on narrow Windows console encodings.

- Added project-specific `usage/` documentation to new-project scaffolding and documented the boundary between project records and personal Vault notes.

- Added `mde docs check` and approval-based managed CLI reference updates for the MDE and Knowledge guides.
- Added the MDE-wide user guide with generated implemented/reserved command status.
- Added Knowledge Plugin 1.2.0 with a safe 30-day audit log retention policy.
- Added Knowledge Plugin 1.1.0 privacy-safe, user-local audit logs for Source lifecycle and scan events.
- Added MDE Knowledge Plugin v1 with source-scoped local Markdown indexing.
- Added safe defaults for personal and work sources, local SQLite search, tags, backlinks, and incremental scanning.
- Added the development record management standard.
- Added dedicated DevelopmentLog and AI request document locations.
- Added Codex, Claude Code, and Gemini request templates.
- Recorded the operational record structure decision and its documentation test.

## 0.9.0

- Added bounded AI automatic test-fix loop.
- Added `inputs.ai.max_fix_attempts` task policy.
- Recorded fix/apply/retest steps in workflow and task results.
