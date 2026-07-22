from pathlib import Path

import pytest

from mde.knowledge.service import KnowledgeService


@pytest.fixture
def knowledge_service(tmp_path: Path) -> KnowledgeService:
    return KnowledgeService(
        registry_path=tmp_path / "user-data" / "sources.json",
        database_path=tmp_path / "user-data" / "knowledge.db",
    )
