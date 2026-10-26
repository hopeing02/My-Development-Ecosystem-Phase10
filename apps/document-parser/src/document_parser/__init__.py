"""Public contract for metadata-only document source validation."""

from document_parser.source import (
    DocumentFormat,
    DocumentSource,
    inspect_document_source,
    validate_source,
)

__all__ = [
    "DocumentFormat",
    "DocumentSource",
    "inspect_document_source",
    "validate_source",
]
