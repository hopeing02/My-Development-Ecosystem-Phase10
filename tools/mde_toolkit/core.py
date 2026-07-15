"""Safe, dependency-free scaffolding functions for My Development Ecosystem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

PROJECT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
DOCUMENT_ID_PATTERN = re.compile(r"^[A-Z]{2,12}-\d{3,}$")

FLOW = [
    ("CON", "01_constitution", "헌법 · 최상위 원칙"),
    ("GOV", "02_governance", "거버넌스 · 역할과 변경 관리"),
    ("STD", "03_standards", "표준 · 문서와 명명 규칙"),
    ("DEV", "04_development", "개발 · 구현 규칙"),
    ("CMD", "05_commands", "명령 · AI 및 도구 명령 체계"),
    ("PRM", "06_prompts", "프롬프트 · 작성 표준"),
    ("ARCH", "07_architecture", "구조 · 시스템 아키텍처"),
    ("SDS", "08_sds", "상세설계 · SDS 색인 및 공통 기준"),
    ("ADR", "09_decisions", "설계 결정 · ADR"),
    ("QA", "10_quality", "품질 · QA 및 검증 기준"),
    ("CODE", "11_code", "구현 · 코드 기준 및 구현 이력"),
    ("TEST", "12_test", "테스트 · 계획과 결과"),
    ("RELEASE", "13_release", "릴리스 · 배포 및 변경 이력"),
    ("OPS", "14_operations", "운영 · 자동화, 워크플로, 에이전트"),
]

CATEGORY_TO_DIRECTORY = {
    "con": "01_constitution",
    "gov": "02_governance",
    "std": "03_standards",
    "dev": "04_development",
    "cmd": "05_commands",
    "prm": "06_prompts",
    "arch": "07_architecture",
    "sds": "08_sds",
    "adr": "09_decisions",
    "qa": "10_quality",
    "code": "11_code",
    "test": "12_test",
    "release": "13_release",
    "ops": "14_operations",
}

PROJECT_DOCUMENT_DIRECTORIES = (
    "SDS",
    "design",
    "API",
    "DB",
    "UI",
    "implementation",
    "tests",
    "releases",
)


@dataclass(frozen=True)
class WriteResult:
    path: Path
    action: str


def validate_project_name(name: str) -> str:
    value = name.strip().lower()
    if not PROJECT_NAME_PATTERN.fullmatch(value):
        raise ValueError(
            "프로젝트명은 영문 소문자로 시작하는 kebab-case여야 합니다. "
            "예: autoknowledge-lite, tax-system"
        )
    return value


def validate_document_id(document_id: str) -> str:
    value = document_id.strip().upper()
    if not DOCUMENT_ID_PATTERN.fullmatch(value):
        raise ValueError("문서 ID는 예: SDS-001, ADR-002 형식이어야 합니다.")
    return value


def package_name(project_name: str) -> str:
    return project_name.replace("-", "_")


def write_file(path: Path, content: str, force: bool = False) -> WriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if existed and not force:
        return WriteResult(path=path, action="skipped")
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return WriteResult(path=path, action="updated" if existed else "created")


def ensure_file(path: Path) -> WriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return WriteResult(path=path, action="skipped")
    path.touch()
    return WriteResult(path=path, action="created")


def _root_readme() -> str:
    return """# My Development Ecosystem (MDE)

개인 AI 개발·지식 운영 생태계를 위한 모노레포입니다.

## 문서 흐름

`CON → GOV → STD → DEV → CMD → PRM → ARCH → SDS → ADR → QA → CODE → TEST → RELEASE`

- 공통 문서: `docs/`
- 공통 프레임워크: `packages/mde-foundation/`
- 제품별 애플리케이션: `apps/`
- 저장소 생성·프로젝트 생성 도구: `tools/`

## 시작

```bash
python tools/init_repository.py
python tools/create_project.py --name autoknowledge-lite --type python
```
"""


def _gitignore() -> str:
    return """# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# Node / Next.js
node_modules/
.next/
dist/
build/

# Environment and secrets
.env
.env.*
!.env.example

# IDE and OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Local logs
*.log
"""


def _root_pyproject() -> str:
    return """[project]
name = "my-development-ecosystem"
version = "0.1.0"
description = "MDE monorepo metadata and development tools"
requires-python = ">=3.12"

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests", "tools/tests"]
"""


def _docs_index() -> str:
    lines = ["# MDE 문서 체계", "", "## 문서 흐름", ""]
    lines.append(
        "`CON → GOV → STD → DEV → CMD → PRM → ARCH → SDS → ADR → QA → CODE → TEST → RELEASE`"
    )
    lines.extend(["", "## 디렉터리", ""])
    for code, directory, description in FLOW:
        lines.append(f"- `{directory}/` — **{code}**: {description}")
    lines.append("- `15_projects/` — 프로젝트별 SDS·설계·API·DB·UI·테스트·릴리스 문서")
    return "\n".join(lines)


def _category_readme(code: str, description: str) -> str:
    return f"""# {code}

{description}

이 디렉터리의 문서는 MDE 문서 흐름과 ID 규칙을 따릅니다.
"""


def _foundation_readme() -> str:
    return """# MDE Foundation

MDE의 공통 Python 프레임워크를 보관합니다.

- `src/mde/`: 공통 패키지
- `tests/`: Foundation 테스트
"""


def _foundation_pyproject() -> str:
    return """[build-system]
requires = ["setuptools>=80"]
build-backend = "setuptools.build_meta"

[project]
name = "mde-foundation"
version = "0.1.0"
description = "Shared foundation package for MDE applications"
requires-python = ">=3.12"

[tool.setuptools.packages.find]
where = ["src"]
"""


def _app_readme(name: str, project_type: str) -> str:
    return f"""# {name}

- 유형: `{project_type}`
- 프로젝트 문서: [`docs/15_projects/{name}/`](../../docs/15_projects/{name}/)

## 시작점

이 애플리케이션의 코드와 테스트는 이 폴더에서 관리합니다. 상세 설계·SDS·API·DB·UI 문서는 중앙 문서 폴더를 단일 원본으로 사용합니다.
"""


def _project_sds_standard(name: str) -> str:
    return f"""# SDS-000 · {name} 프로젝트 상세설계 표준

## 목적

`{name}` 프로젝트의 상세 설계 문서를 작성하는 기준입니다.

## 문서 구성

- `SDS-001-{name}.md`: 프로젝트 개요와 MVP 상세 설계
- `design/`: 화면·흐름·도메인 설계
- `API/`: API 계약
- `DB/`: 데이터 모델
- `UI/`: UI 설계
- `implementation/`: 구현 기록
- `tests/`: 프로젝트 테스트 계획과 결과
- `releases/`: 프로젝트 릴리스 문서
"""


def _project_sds(name: str, project_type: str) -> str:
    return f"""# SDS-001 · {name}

## 1. 프로젝트 개요

- 프로젝트명: `{name}`
- 기술 유형: `{project_type}`
- 상태: 초안

## 2. 목표

프로젝트의 문제, 사용자, 핵심 가치를 작성합니다.

## 3. MVP 범위

- [ ] 핵심 기능 정의
- [ ] 입력·출력 정의
- [ ] 데이터 저장 방식 정의
- [ ] 테스트 기준 정의

## 4. 문서 연결

- 설계: `../design/`
- API: `../API/`
- DB: `../DB/`
- UI: `../UI/`
- 구현: `../implementation/`
- 테스트: `../tests/`
- 릴리스: `../releases/`
"""


def _project_doc_readme(name: str, folder: str) -> str:
    return f"""# {name} · {folder}

이 폴더에는 `{name}` 프로젝트의 {folder} 관련 자료를 보관합니다.
"""


def _generic_document(category: str, document_id: str, title: str) -> str:
    upper = category.upper()
    return f"""# {document_id} · {title}

- 문서 유형: `{upper}`
- 상태: 초안
- 작성일: YYYY-MM-DD
- 변경 이력: CHANGELOG 또는 RELEASE 문서 참조

## 목적

이 문서가 필요한 이유와 해결하려는 문제를 작성합니다.

## 내용

작성합니다.

## 검증 기준

- [ ] 관련 문서와 연결됨
- [ ] 구현·테스트·릴리스 영향 검토 완료
"""


def initialize_repository(root: Path, force: bool = False) -> list[WriteResult]:
    """Create the MDE monorepo baseline without overwriting existing files by default."""
    root = root.expanduser().resolve()
    results: list[WriteResult] = []

    for directory in (
        "apps",
        "archive",
        "examples",
        "packages",
        "prompts",
        "scripts",
        "templates",
        "tests",
        "tools",
        ".github/workflows",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    results.extend(
        [
            write_file(root / "README.md", _root_readme(), force),
            write_file(root / ".gitignore", _gitignore(), force),
            write_file(
                root / "CHANGELOG.md",
                "# Changelog\n\n모든 주요 변경 사항을 기록합니다.",
                force,
            ),
            write_file(root / "pyproject.toml", _root_pyproject(), force),
        ]
    )

    docs_root = root / "docs"
    docs_root.mkdir(parents=True, exist_ok=True)
    results.append(write_file(docs_root / "README.md", _docs_index(), force))

    for code, directory, description in FLOW:
        category_dir = docs_root / directory
        category_dir.mkdir(parents=True, exist_ok=True)
        results.append(
            write_file(
                category_dir / "README.md", _category_readme(code, description), force
            )
        )

    projects_root = docs_root / "15_projects"
    projects_root.mkdir(parents=True, exist_ok=True)
    results.append(
        write_file(
            projects_root / "README.md",
            "# 프로젝트 문서\n\n프로젝트별 SDS·설계·API·DB·UI·테스트·릴리스 문서를 둡니다.",
            force,
        )
    )

    foundation = root / "packages" / "mde-foundation"
    for directory in (
        foundation / "src" / "mde",
        foundation / "tests",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    results.extend(
        [
            write_file(foundation / "README.md", _foundation_readme(), force),
            write_file(foundation / "pyproject.toml", _foundation_pyproject(), force),
            write_file(
                foundation / "src" / "mde" / "__init__.py",
                '__version__ = "0.1.0"',
                force,
            ),
            ensure_file(foundation / "tests" / ".gitkeep"),
        ]
    )

    return results


def create_project(
    root: Path,
    name: str,
    project_type: str = "generic",
    force: bool = False,
) -> list[WriteResult]:
    """Create an application and its central project documentation tree."""
    name = validate_project_name(name)
    project_type = project_type.strip().lower()
    valid_types = {"generic", "python", "gas", "nextjs"}
    if project_type not in valid_types:
        raise ValueError(
            f"프로젝트 유형은 다음 중 하나여야 합니다: {', '.join(sorted(valid_types))}"
        )

    results = initialize_repository(root, force=False)
    root = root.expanduser().resolve()

    app_root = root / "apps" / name
    for directory in (app_root / "src", app_root / "tests", app_root / "docs"):
        directory.mkdir(parents=True, exist_ok=True)
    results.extend(
        [
            write_file(app_root / "README.md", _app_readme(name, project_type), force),
            write_file(
                app_root / "docs" / "README.md",
                f"# {name} 문서 안내\n\n상세 설계의 단일 원본은 `docs/15_projects/{name}/`입니다.",
                force,
            ),
            write_file(
                app_root / ".mde-project.json",
                '{\n  "name": "'
                + name
                + '",\n  "type": "'
                + project_type
                + '",\n  "status": "draft"\n}',
                force,
            ),
        ]
    )

    if project_type == "python":
        module = package_name(name)
        results.extend(
            [
                write_file(
                    app_root / "pyproject.toml",
                    f"""[project]
name = "{name}"
version = "0.1.0"
description = "{name} application"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
                    force,
                ),
                write_file(
                    app_root / "src" / module / "__init__.py",
                    '__version__ = "0.1.0"',
                    force,
                ),
                write_file(
                    app_root / "tests" / "test_smoke.py",
                    f"""def test_project_identity() -> None:
    assert "{name}" == "{name}"
""",
                    force,
                ),
            ]
        )
    elif project_type == "gas":
        results.extend(
            [
                write_file(
                    app_root / "src" / "appsscript.json",
                    '{\n  "timeZone": "Asia/Seoul",\n  "exceptionLogging": "STACKDRIVER",\n  "runtimeVersion": "V8"\n}',
                    force,
                ),
                write_file(
                    app_root / "src" / "Code.gs",
                    f"""/** Entry point for {name}. */
function onOpen() {{
  SpreadsheetApp.getUi().createMenu('{name}').addItem('Open', 'showApp').addToUi();
}}

function showApp() {{
  SpreadsheetApp.getUi().alert('{name} scaffold is ready.');
}}
""",
                    force,
                ),
                ensure_file(app_root / "tests" / ".gitkeep"),
            ]
        )
    elif project_type == "nextjs":
        results.extend(
            [
                write_file(
                    app_root / "package.json",
                    f"""{{
  "name": "{name}",
  "private": true,
  "version": "0.1.0",
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }}
}}
""",
                    force,
                ),
                write_file(
                    app_root / "src" / "app" / "page.tsx",
                    f"""export default function Home() {{
  return <main><h1>{name}</h1><p>MDE project scaffold</p></main>;
}}
""",
                    force,
                ),
                ensure_file(app_root / "tests" / ".gitkeep"),
            ]
        )
    else:
        results.extend(
            [
                ensure_file(app_root / "src" / ".gitkeep"),
                ensure_file(app_root / "tests" / ".gitkeep"),
            ]
        )

    docs_root = root / "docs" / "15_projects" / name
    for directory in PROJECT_DOCUMENT_DIRECTORIES:
        (docs_root / directory).mkdir(parents=True, exist_ok=True)
    results.extend(
        [
            write_file(
                docs_root / "README.md",
                f"# {name} 프로젝트 문서\n\n이 폴더가 `{name}`의 설계 문서 단일 원본입니다.",
                force,
            ),
            write_file(
                docs_root / "SDS" / "SDS-000-project-standard.md",
                _project_sds_standard(name),
                force,
            ),
            write_file(
                docs_root / "SDS" / f"SDS-001-{name}.md",
                _project_sds(name, project_type),
                force,
            ),
        ]
    )
    for directory in PROJECT_DOCUMENT_DIRECTORIES:
        if directory != "SDS":
            results.append(
                write_file(
                    docs_root / directory / "README.md",
                    _project_doc_readme(name, directory),
                    force,
                )
            )

    return results


def create_document(
    root: Path,
    category: str,
    document_id: str,
    title: str,
    project: str | None = None,
    force: bool = False,
) -> WriteResult:
    """Create a controlled document in the global or project-specific document tree."""
    category = category.strip().lower()
    if category not in CATEGORY_TO_DIRECTORY:
        raise ValueError("지원 문서 유형: " + ", ".join(sorted(CATEGORY_TO_DIRECTORY)))
    document_id = validate_document_id(document_id)
    title = title.strip()
    if not title:
        raise ValueError("문서 제목을 입력해야 합니다.")

    initialize_repository(root, force=False)
    root = root.expanduser().resolve()

    if project:
        project = validate_project_name(project)
        target_dir = (
            root / "docs" / "15_projects" / project / "SDS"
            if category == "sds"
            else root / "docs" / "15_projects" / project / "design"
        )
    else:
        target_dir = root / "docs" / CATEGORY_TO_DIRECTORY[category]

    filename = f"{document_id}-{title.lower().replace(' ', '-')}.md"
    filename = re.sub(r"[^A-Za-z0-9가-힣._-]", "-", filename)
    return write_file(
        target_dir / filename, _generic_document(category, document_id, title), force
    )
