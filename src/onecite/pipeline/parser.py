# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 1 — parse and extract raw entries from text/BibTeX input."""

import re
import logging
from typing import List

import bibtexparser

from ..core import RawEntry
from ..exceptions import ParseError

_BIBTEX_ENTRY_START_RE = re.compile(r"(?m)^[ \t]*@(?P<entry_type>[A-Za-z]+)\s*(?P<opening>[{(])")
_BIBTEX_SPECIAL_TYPES = {"comment", "preamble", "string"}


def _matching_entry_end(content: str, body_start: int, opening: str) -> int | None:
    """Return the closing-delimiter position for one complete BibTeX entry."""
    closing = "}" if opening == "{" else ")"
    outer_depth = 1
    brace_depth = 0
    in_quote = False
    escaped = False
    for index in range(body_start, len(content)):
        char = content[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if opening == "(":
            if char == "{":
                brace_depth += 1
            elif char == "}" and brace_depth:
                brace_depth -= 1
            elif brace_depth == 0 and char == opening:
                outer_depth += 1
            elif brace_depth == 0 and char == closing:
                outer_depth -= 1
        else:
            if char == opening:
                outer_depth += 1
            elif char == closing:
                outer_depth -= 1
        if outer_depth == 0:
            return index
    return None


def _top_level_segments(value: str) -> list[str]:
    """Split comma-delimited BibTeX content outside braces and quotes."""
    segments: list[str] = []
    start = 0
    brace_depth = 0
    paren_depth = 0
    in_quote = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}" and brace_depth:
            brace_depth -= 1
        elif brace_depth == 0 and char == "(":
            paren_depth += 1
        elif brace_depth == 0 and char == ")" and paren_depth:
            paren_depth -= 1
        elif char == "," and brace_depth == 0 and paren_depth == 0:
            segments.append(value[start:index])
            start = index + 1
    segments.append(value[start:])
    return segments


def _duplicate_bibtex_fields(content: str) -> list[tuple[str, list[str]]]:
    """Find case-insensitive duplicate fields within complete BibTeX entries."""
    duplicates: list[tuple[str, list[str]]] = []
    cursor = 0
    while match := _BIBTEX_ENTRY_START_RE.search(content, cursor):
        entry_type = match.group("entry_type").lower()
        opening = match.group("opening")
        body_start = match.end()
        body_end = _matching_entry_end(content, body_start, opening)
        if body_end is None:
            break
        cursor = body_end + 1
        if entry_type in _BIBTEX_SPECIAL_TYPES:
            continue
        segments = _top_level_segments(content[body_start:body_end])
        if len(segments) < 2:
            continue
        entry_key = segments[0].strip() or "<empty>"
        seen: set[str] = set()
        repeated: set[str] = set()
        for segment in segments[1:]:
            field_match = re.match(r"\s*([A-Za-z][A-Za-z0-9_+().-]*)\s*=", segment)
            if not field_match:
                continue
            field_name = field_match.group(1).lower()
            if field_name in seen:
                repeated.add(field_name)
            seen.add(field_name)
        if repeated:
            duplicates.append((entry_key, sorted(repeated)))
    return duplicates


class ParserModule:
    """Stage 1: Parse and Extract Module"""

    def __init__(self):
        """Initialize the parser module."""
        self.logger = logging.getLogger(__name__)

    def parse(self, input_content: str, input_type: str) -> List[RawEntry]:
        """Parse input content into a list of raw entries.

        Args:
            input_content: The raw text or BibTeX string to parse.
            input_type: ``"txt"`` for plain-text references or
                ``"bib"`` for BibTeX format.

        Returns:
            A list of :class:`RawEntry` dictionaries.
        """
        self.logger.info(f"Starting to parse {input_type} format input content")

        if input_type.lower() == "bib":
            return self._parse_bibtex(input_content)
        elif input_type.lower() == "txt":
            return self._parse_text(input_content)
        else:
            raise ParseError(f"Unsupported input type: {input_type}")

    def _parse_bibtex(self, bibtex_content: str) -> List[RawEntry]:
        """Parse BibTeX format content"""
        entries = []
        try:
            # bibtexparser drops non-standard entry types (@software,
            # @dataset, ...) by default — OneCite emits @software itself, so
            # its own output must survive a round-trip through bib input.
            bibtex_parser = bibtexparser.bparser.BibTexParser(
                ignore_nonstandard_types=False, common_strings=True
            )
            bib_database = bibtexparser.loads(bibtex_content, parser=bibtex_parser)
            duplicate_fields = _duplicate_bibtex_fields(bibtex_content)
            if duplicate_fields:
                details = "; ".join(
                    f"{entry_key}: {', '.join(fields)}" for entry_key, fields in duplicate_fields
                )
                raise ParseError(f"Duplicate BibTeX fields are not allowed ({details}).")
            if bibtex_content.strip() and not bib_database.entries:
                # Silently returning zero entries would let the pipeline
                # report an empty success for a non-empty file.
                raise ParseError(
                    "No BibTeX entries could be parsed from the input; "
                    "check the file syntax and entry types."
                )
            for i, entry in enumerate(bib_database.entries):
                original_entry = dict(entry)

                self.logger.debug(f"Entry {i}: original fields: {list(original_entry.keys())}")

                raw_entry: RawEntry = {
                    "id": i,
                    "raw_text": str(entry),
                    "doi": entry.get("doi"),
                    "url": entry.get("url"),
                    "query_string": None,
                    "original_entry": original_entry,
                }

                # Always build a human-readable query string from the
                # structured fields. Identification prefers the DOI when one
                # is present, but suggest-style flows fall back to the query
                # string — and falling back to ``str(entry)`` would send a
                # Python dict repr to the scholarly indexes as a search query.
                query_parts = []
                if "title" in entry:
                    query_parts.append(entry["title"])
                if "author" in entry:
                    query_parts.append(entry["author"])
                if "year" in entry:
                    query_parts.append(entry["year"])
                raw_entry["query_string"] = " ".join(query_parts) or None

                entries.append(raw_entry)

            self.logger.info(f"Successfully parsed {len(entries)} BibTeX entries")
            return entries

        except ParseError:
            raise
        except Exception as e:
            self.logger.error(f"BibTeX parsing failed: {str(e)}")
            raise ParseError(f"BibTeX parsing failed: {str(e)}")

    def _parse_text(self, text_content: str) -> List[RawEntry]:
        """Parse plain text format content"""
        entries: List[RawEntry] = []

        # Split text blocks using double newlines
        text_blocks = text_content.split("\n\n")

        for block in text_blocks:
            block = block.strip()
            if not block:
                continue

            raw_entry: RawEntry = {
                # Running index over non-empty blocks so ids stay contiguous
                # even when entries are separated by more than one blank line
                # (which yields empty splits that are skipped above).
                "id": len(entries),
                "raw_text": block,
                "doi": None,
                "url": None,
                "query_string": None,
            }

            doi_match = re.search(r"10\.\d{4,}/[^\s,}]+", block)
            if doi_match:
                raw_entry["doi"] = doi_match.group().rstrip(".,;:)]")

            url_match = re.search(r"https?://[^\s]+", block)
            if url_match:
                raw_entry["url"] = url_match.group()

            # If no DOI or URL found, build a concise query string from title/author/year
            if not raw_entry["doi"] and not raw_entry["url"]:
                # Check if block is a bare PMID (7-8 digits, optionally prefixed with "PMID:")
                if re.match(r"^(PMID:?\s*)?\d{7,8}$", block.strip(), re.IGNORECASE):
                    raw_entry["query_string"] = block.strip()
                else:
                    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
                    title_text = lines[0] if lines else block
                    authors_text = lines[1] if len(lines) > 1 else ""
                    year_match = re.search(r"(19|20)\d{2}", block)
                    year_text = year_match.group(0) if year_match else ""

                    query_parts: List[str] = []
                    if title_text:
                        query_parts.append(title_text)
                    if authors_text:
                        query_parts.append(authors_text)
                    if year_text:
                        query_parts.append(year_text)

                    raw_entry["query_string"] = " ".join(query_parts) or block

            entries.append(raw_entry)

        self.logger.info(f"Successfully parsed {len(entries)} text entries")
        return entries
