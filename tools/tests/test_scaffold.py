from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.mde_toolkit.core import (
    create_document,
    create_project,
    initialize_repository,
)


class ScaffoldTests(unittest.TestCase):
    def test_initialize_repository_creates_document_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "mde"
            initialize_repository(root)

            self.assertTrue((root / "docs" / "01_constitution" / "README.md").exists())
            self.assertTrue((root / "docs" / "08_sds" / "README.md").exists())
            self.assertTrue((root / "docs" / "15_projects" / "README.md").exists())
            self.assertFalse((root / "docs" / "CON").exists())

    def test_create_python_project_creates_app_and_sds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "mde"
            create_project(root, "senior-matching", "python")

            self.assertTrue(
                (
                    root
                    / "apps"
                    / "senior-matching"
                    / "src"
                    / "senior_matching"
                    / "__init__.py"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "docs"
                    / "15_projects"
                    / "senior-matching"
                    / "SDS"
                    / "SDS-001-senior-matching.md"
                ).exists()
            )

    def test_create_controlled_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "mde"
            result = create_document(root, "adr", "ADR-002", "Monorepo Rule")

            self.assertEqual(result.action, "created")
            self.assertTrue(
                (root / "docs" / "09_decisions" / "ADR-002-monorepo-rule.md").exists()
            )


if __name__ == "__main__":
    unittest.main()
