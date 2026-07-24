# Changelog

모든 주요 변경 사항을 기록합니다.

## Unreleased

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
