# DOC-PARSER-2 — HWPX paragraph extraction (frozen execution specification)

Date: 2026-11-01. Baseline: 16a5b5cb75a00bce392e22ee8487a9ff99fa7fd3.
Batch: DOC-PARSER-2-VALIDATION. Preparation: validation/doc-parser-2-base.
Execution: validation/doc-parser-2-exec. Do not change this specification during execution.

## Public contract

Create document_parser.paragraphs.extract_hwpx_paragraphs(file_path: str | Path) -> list[str].
Call the existing public inspect_document_source(file_path) for validation and expanded input path.
Do not duplicate input validation. Reject supported non-HWPX sources with ValueError before opening ZIP.
Only use the standard library and existing project code; add no dependencies.
Open the source ZIP read-only, never extract it or modify the source.
Match section members exactly with Contents/section followed by one or more digits and .xml.
Sort sections by integer section number, independent of archive order.
Parse sections with ElementTree. Recognize p and t using local names (namespace prefix/URI independent).
For each p in XML document order, concatenate itertext() of descendant t elements in document order.
Preserve Unicode and all original whitespace; do not strip or add paragraph separators.
Keep empty paragraphs as empty strings. Sections without p contribute no paragraphs; all-empty sections return [].
No matching sections: ValueError. Bad ZIP: ValueError with original BadZipFile as cause.
Malformed section XML: ValueError identifying the section, retaining ParseError as cause.
Propagate filesystem/input validation errors unchanged. Do not change extract_hwpx_text behavior.
Table/image/layout reconstruction, OCR, resource limits and DOC-PARSER-3 are excluded.

## STEP 2A

Allowed artifacts (both required):
- apps/document-parser/src/document_parser/paragraphs.py
- apps/document-parser/tests/test_paragraphs.py

Implement the public function and meaningful basic tests: multiple paragraphs, multiple numeric-ordered sections,
whitespace/Unicode, empty paragraphs and reuse of inspect_document_source.
Tests use synthetic ZIP/XML only. Verify source bytes are unchanged.

## STEP 2B

Required artifact:
- apps/document-parser/tests/test_paragraphs_edge_cases.py
Optional minimal correction only:
- apps/document-parser/src/document_parser/paragraphs.py

Reuse the actual 2A module and tests supplied in context. Add boundary/regression tests for namespace variants,
empty sections, exact section names, non-HWPX, bad ZIP/XML, missing sections, input errors and source immutability.
Do not replace or weaken 2A tests. Do not invent unsupported input limits.

## Protected files and validation

Do not change source.py, hwpx.py, __init__.py, existing tests, MDE core, W1, specification or workflow.
Return full artifact contents; use only supplied context. No commands, edits, delegation, commits or pushes by Codex.
MDE performs review, artifact allowlist checks, apply, pytest, Ruff, Black and change-list checks in that order.
No automatic fix loop. A failed check stops the batch. G2 alone commits completed STEP results.
Git task state movements and status/mobile-summary.json are expected MDE bookkeeping, separate from code allowlists.
Final report is written only after external verification; do not generate a PASS report as an AI artifact.

## Operator command

After approved remote registration of preparation branch and a clean worktree:
MDE_CODEX_TIMEOUT=1800; uv run mde agent --once --auto-save --no-push
The explicit --auto-save is required by the current Agent with --no-push.
Never merge to main automatically. Keep logs/checkpoints and failed worktree for inspection.
