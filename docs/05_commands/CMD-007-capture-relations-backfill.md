# CMD-007 Capture 관계 Backfill

## Dry-run

```powershell
uv run --project apps/autoknowledge-lite autoknowledge-lite capture-relations backfill `
  --dry-run `
  --from-date 2026-07-01 `
  --to-date 2026-08-31
```

## 실제 실행

```powershell
uv run --project apps/autoknowledge-lite autoknowledge-lite capture-relations backfill `
  --project autoknowledge-lite `
  --limit 500
```

필요하면 `--data-dir`, `--vault-dir`, `--mde-codex-home`, `--no-auto-confirm`을 지정한다. dry-run은 임시 인덱스를 사용하므로 운영 관계·문서·인덱스를 변경하지 않는다.
