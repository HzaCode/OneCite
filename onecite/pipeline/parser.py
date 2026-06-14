# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 1 — parse and extract raw entries from text/BibTeX input."""

import re
import logging
from typing import List

import bibtexparser

from ..core import RawEntry
from ..exceptions import ParseError


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
            bib_database = bibtexparser.loads(bibtex_content)
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

                # If no DOI is available, generate query string
                if not raw_entry["doi"]:
                    query_parts = []
                    if "title" in entry:
                        query_parts.append(entry["title"])
                    if "author" in entry:
                        query_parts.append(entry["author"])
                    if "year" in entry:
                        query_parts.append(entry["year"])
                    raw_entry["query_string"] = " ".join(query_parts)

                entries.append(raw_entry)

            self.logger.info(f"Successfully parsed {len(entries)} BibTeX entries")
            return entries

        except Exception as e:
            self.logger.error(f"BibTeX parsing failed: {str(e)}")
            raise ParseError(f"BibTeX parsing failed: {str(e)}")

    def _parse_text(self, text_content: str) -> List[RawEntry]:
        """Parse plain text format content"""
        entries = []

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
