"""Extract section text from HWPX without modifying or unpacking the source."""

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from document_parser import DocumentSource, inspect_document_source


def extract_hwpx_text(file_path: str | Path) -> str:
    """Return numerically ordered section text, preserving its whitespace.

    Source validation errors propagate unchanged. Invalid ZIP or section XML,
    missing sections and supported non-HWPX sources raise ValueError.
    """
    source: DocumentSource = inspect_document_source(file_path)
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

            texts = []
            for _, member in sections:
                try:
                    root = ElementTree.fromstring(archive.read(member))
                except ElementTree.ParseError as error:
                    raise ValueError(
                        f"Invalid HWPX section XML: {member.filename}"
                    ) from error
                texts.append(
                    "".join(
                        "".join(element.itertext())
                        for element in root.iter()
                        if element.tag.rsplit("}", 1)[-1] == "t"
                    )
                )
            return "\n".join(texts)
    except BadZipFile as error:
        raise ValueError("Invalid HWPX ZIP") from error
