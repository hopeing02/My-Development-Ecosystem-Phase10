"""Local, source-scoped Markdown knowledge indexing for MDE."""

from mde.knowledge.graph import KnowledgeGraphService
from mde.knowledge.models import (
    KnowledgeDocument,
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeSource,
    SearchResult,
)
from mde.knowledge.service import KnowledgeService

__version__ = "1.2.0"

__all__ = [
    "KnowledgeDocument",
    "KnowledgeGraph",
    "KnowledgeGraphEdge",
    "KnowledgeGraphNode",
    "KnowledgeGraphService",
    "KnowledgeService",
    "KnowledgeSource",
    "SearchResult",
    "__version__",
]
