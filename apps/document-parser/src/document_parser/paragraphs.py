"""Extract HWPX paragraphs without modifying or unpacking the source."""

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from document_parser import inspect_document_source


def extract_hwpx_paragraphs(file_path: str | Path) -> list[str]:
    """Return paragraphs with each text node owned by its nearest paragraph.

    Keep document-order paragraph elements and original text whitespace. Nested
    paragraphs do not donate their text to any enclosing paragraph.
    """
    source = inspect_document_source(file_path)
    if source.format != "hwpx":
        raise ValueError("Expected HWPX document source")

    try:
        with ZipFile(source.path, "r") as archive:
            sections = []
            for member in archive.infolist():
                match = re.fullmatch(r"Contents/section(\d+)\.xml", member.filename)
                if match is not None:
                    sections.append((int(match.group(1)), member))
            sections.sort(key=lambda section: section[0])
            if not sections:
                raise ValueError("HWPX contains no section XML")

            paragraphs: list[str] = []
            for _, member in sections:
                try:
                    root = ElementTree.fromstring(archive.read(member))
                except ElementTree.ParseError as error:
                    raise ValueError(
                        f"Invalid HWPX section XML: {member.filename}"
                    ) from error

                parts: list[list[str]] = []
                stack: list[tuple[ElementTree.Element, int | None]] = [(root, None)]
                while stack:
                    element, owner = stack.pop()
                    name = element.tag.rsplit("}", 1)[-1]
                    if name == "p":
                        owner = len(parts)
                        parts.append([])
                    if name == "t":
                        if owner is not None:
                            parts[owner].append("".join(element.itertext()))
                        continue
                    stack.extend((child, owner) for child in reversed(element))
                paragraphs.extend("".join(content) for content in parts)
            return paragraphs
    except BadZipFile as error:
        raise ValueError("Invalid HWPX ZIP") from error
