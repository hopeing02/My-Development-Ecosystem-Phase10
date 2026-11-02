"""Extract HWPX paragraphs without modifying or unpacking the source."""

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from document_parser import inspect_document_source


def extract_hwpx_paragraphs(file_path: str | Path) -> list[str]:
    """Return paragraphs from numerically ordered sections, preserving whitespace.

    Source validation errors propagate unchanged. Invalid ZIP or section XML,
    missing sections and supported non-HWPX sources raise ValueError.
    Empty paragraphs are retained; sections without paragraphs contribute nothing.
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

            paragraphs = []
            for _, member in sections:
                try:
                    root = ElementTree.fromstring(archive.read(member))
                except ElementTree.ParseError as error:
                    raise ValueError(
                        f"Invalid HWPX section XML: {member.filename}"
                    ) from error
                for paragraph in root.iter():
                    if paragraph.tag.rsplit("}", 1)[-1] == "p":
                        paragraphs.append(
                            "".join(
                                "".join(element.itertext())
                                for element in paragraph.iter()
                                if element.tag.rsplit("}", 1)[-1] == "t"
                            )
                        )
            return paragraphs
    except BadZipFile as error:
        raise ValueError("Invalid HWPX ZIP") from error
