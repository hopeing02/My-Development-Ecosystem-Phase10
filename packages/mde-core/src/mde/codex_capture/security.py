from __future__ import annotations

import os
import re
from pathlib import Path

SENSITIVE_FILE_PATTERNS = (
    re.compile(r"(^|/)\.env(?:\..*)?$", re.IGNORECASE),
    re.compile(r"\.(?:pem|key|pfx|p12)$", re.IGNORECASE),
    re.compile(r"(^|/)(?:id_rsa|id_ed25519)$", re.IGNORECASE),
    re.compile(
        r"(^|/)(?:\.aws|\.ssh|\.git|node_modules|\.venv|venv)(/|$)", re.IGNORECASE
    ),
)

SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|ghp|gho|github_pat)-?[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(
        r"(?i)(\b(?:password|passwd|secret|api[_-]?key|oauth[_-]?token|"
        r"access[_-]?token)\s*[:=]\s*)[^\s\"']{4,}"
    ),
    re.compile(r"(?i)([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*=\s*)[^\s]+"),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s]+"),
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
)


def is_sensitive_path(path: str | Path) -> bool:
    normalized = str(path).replace("\\", "/")
    return any(pattern.search(normalized) for pattern in SENSITIVE_FILE_PATTERNS)


def redact_text(value: str) -> tuple[str, bool]:
    redacted = value
    changed = False
    for pattern in SECRET_PATTERNS:
        replacement = r"\1[REDACTED]" if pattern.groups else "[REDACTED]"
        redacted, count = pattern.subn(replacement, redacted)
        changed = changed or count > 0
    return redacted, changed


def alias_path(path: str | Path, *, repo_root: Path, worktree_root: Path) -> str:
    resolved = str(Path(path).resolve())
    candidates: list[tuple[str, str]] = [
        (str(worktree_root.resolve()), "%WORKTREE_ROOT%"),
        (str(repo_root.resolve()), "%REPO_ROOT%"),
    ]
    profile = os.environ.get("USERPROFILE")
    if profile:
        candidates.append((str(Path(profile).resolve()), "%USERPROFILE%"))
    candidates.sort(key=lambda item: len(item[0]), reverse=True)
    folded = resolved.casefold()
    for prefix, alias in candidates:
        if folded == prefix.casefold():
            return alias
        marker = prefix.rstrip("\\/") + os.sep
        if folded.startswith(marker.casefold()):
            suffix = resolved[len(marker) :].replace("\\", "/")
            return f"{alias}/{suffix}"
    return resolved.replace("\\", "/")


def alias_text(value: str, *, repo_root: Path, worktree_root: Path) -> str:
    replacements: list[tuple[str, str]] = [
        (str(worktree_root.resolve()), "%WORKTREE_ROOT%"),
        (str(repo_root.resolve()), "%REPO_ROOT%"),
    ]
    profile = os.environ.get("USERPROFILE")
    if profile:
        replacements.append((str(Path(profile).resolve()), "%USERPROFILE%"))
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    output = value
    for prefix, alias in replacements:
        output = re.sub(re.escape(prefix), alias, output, flags=re.IGNORECASE)
        output = re.sub(
            re.escape(prefix.replace("\\", "/")),
            alias,
            output,
            flags=re.IGNORECASE,
        )
    return (
        output.replace("\\", "/")
        if any(alias in output for _, alias in replacements)
        else output
    )
