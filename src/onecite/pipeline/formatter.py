# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 4 — format completed entries into BibTeX or CSL-JSON output."""

import json
import logging
import re
from typing import List, Dict, Any

import bibtexparser

from ..core import CompletedEntry
from ..exceptions import FormatError

# Human-readable explanations for the failure reason codes attached by the
# identifier and enricher stages. A failed entry must tell the user *why* it
# failed: a safely rejected identifier, an ambiguous reference, and an
# unavailable source all require different follow-up actions.
FAILURE_MESSAGES = {
    "doi_not_found": (
        "DOI not found in CrossRef or DataCite — likely fabricated or mistyped; "
        "no citation was emitted for it"
    ),
    "source_error": "A bibliographic source errored during lookup; retry may succeed",
    "pmid_unresolved": "PMID lookup returned no record (nonexistent PMID or source unavailable)",
    "isbn_unresolved": (
        "ISBN lookup returned no record (nonexistent ISBN or source unavailable/rate-limited)"
    ),
    "no_strong_identifier": (
        "No strong identifier (DOI/PMID/arXiv/URL) found; use `onecite suggest` "
        "to search candidates for review"
    ),
    "url_unresolved": "URL did not yield a resolvable identifier",
    "no_identifier_data": "Entry was identified but carried no identifier data",
    "metadata_unavailable": "No source returned metadata for the resolved identifier",
    "enrichment_error": "Metadata enrichment failed",
    "unresolved": "Entry processing failed",
}

# BibTeX entry types mapped onto CSL-JSON item types
# (https://docs.citationstyles.org/en/stable/specification.html).
CSL_TYPES = {
    "article": "article-journal",
    "inproceedings": "paper-conference",
    "incollection": "chapter",
    "book": "book",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "techreport": "report",
    "software": "software",
    "dataset": "dataset",
    "misc": "document",
}


class FormatterModule:
    """Stage 4: Formatting and Generation Module."""

    def __init__(self):
        """Initialize the formatter module."""
        self.logger = logging.getLogger(__name__)

        # LaTeX character escape mapping for common Unicode characters
        self.unicode_to_latex = {
            "ä": r"{\"a}",
            "Ä": r"{\"A}",
            "ë": r"{\"e}",
            "Ë": r"{\"E}",
            "ï": r"{\"i}",
            "Ï": r"{\"I}",
            "ö": r"{\"o}",
            "Ö": r"{\"O}",
            "ü": r"{\"u}",
            "Ü": r"{\"U}",
            "ÿ": r"{\"y}",
            "Ÿ": r"{\"Y}",
            "á": r"{\'a}",
            "Á": r"{\'A}",
            "é": r"{\'e}",
            "É": r"{\'E}",
            "í": r"{\'i}",
            "Í": r"{\'I}",
            "ó": r"{\'o}",
            "Ó": r"{\'O}",
            "ú": r"{\'u}",
            "Ú": r"{\'U}",
            "ý": r"{\'y}",
            "Ý": r"{\'Y}",
            "à": r"{\`a}",
            "À": r"{\`A}",
            "è": r"{\`e}",
            "È": r"{\`E}",
            "ì": r"{\`i}",
            "Ì": r"{\`I}",
            "ò": r"{\`o}",
            "Ò": r"{\`O}",
            "ù": r"{\`u}",
            "Ù": r"{\`U}",
            "â": r"{\^a}",
            "Â": r"{\^A}",
            "ê": r"{\^e}",
            "Ê": r"{\^E}",
            "î": r"{\^i}",
            "Î": r"{\^I}",
            "ô": r"{\^o}",
            "Ô": r"{\^O}",
            "û": r"{\^u}",
            "Û": r"{\^U}",
            "ã": r"{\~a}",
            "Ã": r"{\~A}",
            "ñ": r"{\~n}",
            "Ñ": r"{\~N}",
            "õ": r"{\~o}",
            "Õ": r"{\~O}",
            "å": r"{\aa}",
            "Å": r"{\AA}",
            "ø": r"{\o}",
            "Ø": r"{\O}",
            "æ": r"{\ae}",
            "Æ": r"{\AE}",
            "œ": r"{\oe}",
            "Œ": r"{\OE}",
            "ß": r"{\ss}",
            "ç": r"{\c{c}}",
            "Ç": r"{\c{C}}",
            "ł": r"{\l}",
            "Ł": r"{\L}",
            "–": "--",  # en-dash
            "—": "---",  # em-dash
            "‘": "`",
            "’": "'",  # curly single quotes
            "“": "``",
            "”": "''",  # curly double quotes
        }

    def _escape_latex_chars(self, text: str) -> str:
        """Convert Unicode characters to LaTeX escape sequences."""
        if not text:
            return text

        result = str(text)

        # Don't escape if text already contains BibTeX LaTeX commands
        # (e.g., K{"u}nsch should stay as-is, not convert " to '')
        # Check for patterns like {\"x} or {"x}
        has_latex_commands = bool(re.search(r'\{[\\"]', result))

        if has_latex_commands:
            # The value already contains LaTeX escapes (e.g. {\"u}); leave it
            # untouched so existing commands are not corrupted or double-escaped.
            return result

        # Replace Unicode characters with LaTeX equivalents
        for unicode_char, latex_escape in self.unicode_to_latex.items():
            result = result.replace(unicode_char, latex_escape)

        return result

    def format(self, completed_entries: List[CompletedEntry], output_format: str) -> Dict[str, Any]:
        """Format completed records to the specified output format.

        Args:
            completed_entries: List of completed entries from
                :meth:`EnricherModule.enrich`.
            output_format: Output format — ``"bibtex"`` or
                ``"csl-json"``; any other value raises ``FormatError``.

        Returns:
            A dictionary with two keys:

            * ``results`` — a list of formatted citation strings (BibTeX
              entries or CSL-JSON item objects, one per unique resolved
              work; repeated DOIs are reported, not re-emitted).
            * ``report`` — a dict with ``total``, ``succeeded``,
              ``failed_entries``, ``warnings`` (non-blocking review warnings
              attached to resolved entries), and ``duplicates`` (entries whose
              DOI already resolved earlier in the batch).
        """
        self.logger.info(
            "Starting to format %s entries to %s format",
            len(completed_entries),
            output_format,
        )

        formatted_strings = []
        failed_entries = []
        warnings = []
        duplicates = []
        # Map of normalized DOI -> first entry that resolved to it. The same
        # work commonly appears several times in a messy reference list under
        # different spellings (bare DOI, PMID, formatted citation); emitting
        # it repeatedly under suffixed keys would just move the mess into the
        # output, so later occurrences are reported as duplicates instead.
        seen_dois: Dict[str, Dict[str, Any]] = {}

        for entry in completed_entries:
            if entry["status"] == "completed":
                try:
                    doi_key = (
                        (entry.get("doi") or entry.get("bib_data", {}).get("doi") or "")
                        .strip()
                        .lower()
                    )
                    if doi_key and doi_key in seen_dois:
                        first = seen_dois[doi_key]
                        duplicates.append(
                            {
                                "id": entry["id"],
                                "doi": doi_key,
                                "duplicate_of": first["id"],
                                "bib_key": first["bib_key"],
                                "raw_text": (entry.get("raw_text") or "")[:200],
                            }
                        )
                        continue

                    if output_format.lower() == "bibtex":
                        formatted_string = self._format_bibtex(entry)
                    elif output_format.lower() == "csl-json":
                        formatted_string = self._format_csl_json(entry)
                    else:
                        raise FormatError(
                            f"Unsupported output format: {output_format!r}. "
                            "Supported formats: 'bibtex', 'csl-json'."
                        )

                    formatted_strings.append(formatted_string)
                    if doi_key:
                        seen_dois[doi_key] = {
                            "id": entry["id"],
                            "bib_key": entry.get("bib_key", ""),
                        }
                    for warning in entry.get("warnings") or []:
                        warnings.append({"id": entry["id"], **warning})

                except Exception as e:
                    self.logger.error(f"Formatting entry {entry['id']} failed: {str(e)}")
                    failed_entries.append(
                        {"id": entry["id"], "error": str(e), "doi": entry.get("doi", "unknown")}
                    )
            else:
                reason = entry.get("failure_reason", "unresolved")
                failed_entries.append(
                    {
                        "id": entry["id"],
                        "error": FAILURE_MESSAGES.get(reason, "Entry processing failed"),
                        "status": entry["status"],
                        "reason": reason,
                        "raw_text": (entry.get("raw_text") or "")[:200],
                    }
                )

        report = {
            "total": len(completed_entries),
            "succeeded": len(formatted_strings),
            "failed_entries": failed_entries,
            "warnings": warnings,
            "duplicates": duplicates,
        }

        self.logger.info(
            "Formatting completed: %s/%s entries successful",
            len(formatted_strings),
            len(completed_entries),
        )

        return {"results": formatted_strings, "report": report}

    @staticmethod
    def _csl_plain(value: Any) -> str:
        """Convert a BibTeX field value to CSL plain text.

        Braces are LaTeX case-protection markup with no meaning in CSL —
        remove them all (``str.strip`` would mangle inner braces like
        ``{ResNet}: ...`` into unbalanced text).
        """
        return re.sub(r"[{}]", "", str(value)).strip()

    def _format_csl_json(self, entry: CompletedEntry) -> str:
        """Format one entry as a CSL-JSON item (a JSON object string).

        CSL-JSON wants plain Unicode, so the raw metadata values are used
        directly — LaTeX escaping applies only to BibTeX output.
        """
        bib_data = entry["bib_data"]
        item: Dict[str, Any] = {
            "id": bib_data.get("ID", entry.get("bib_key", "")),
            "type": CSL_TYPES.get(str(bib_data.get("ENTRYTYPE", "article")).lower(), "document"),
        }
        if bib_data.get("title"):
            item["title"] = self._csl_plain(bib_data["title"])
        authors = self._parse_bibtex_authors(str(bib_data.get("author", "")))
        if authors:
            item["author"] = authors
        container = bib_data.get("journal") or bib_data.get("booktitle")
        if container:
            item["container-title"] = self._csl_plain(container)
        if bib_data.get("year"):
            try:
                item["issued"] = {"date-parts": [[int(self._csl_plain(bib_data["year"]))]]}
            except ValueError:
                pass
        for bibtex_field, csl_field in (
            ("volume", "volume"),
            ("number", "issue"),
            ("pages", "page"),
            ("publisher", "publisher"),
            ("doi", "DOI"),
            ("url", "URL"),
            ("abstract", "abstract"),
            ("isbn", "ISBN"),
            ("note", "note"),
        ):
            value = bib_data.get(bibtex_field)
            if value:
                item[csl_field] = self._csl_plain(value)
        # BibTeX page ranges use the LaTeX "--" en-dash convention; CSL is
        # plain text.
        if "page" in item:
            item["page"] = item["page"].replace("--", "-")
        return json.dumps(item, ensure_ascii=False, indent=2)

    @staticmethod
    def _parse_bibtex_authors(author_field: str) -> List[Dict[str, str]]:
        """Parse a BibTeX author string into CSL name objects.

        ``"Family, Given"`` parts become structured names; parts without a
        comma (organizations, single-token names) become literal names
        rather than being guessed apart.
        """
        names = []
        author_field = re.sub(r"[{}]", "", author_field)
        for part in re.split(r"\s+and\s+", author_field.strip()):
            part = part.strip()
            if not part:
                continue
            if "," in part:
                family, _, given = part.partition(",")
                name = {"family": family.strip()}
                if given.strip():
                    name["given"] = given.strip()
                names.append(name)
            else:
                names.append({"literal": part})
        return names

    def _format_bibtex(self, entry: CompletedEntry) -> str:
        """Format to BibTeX using bibtexparser.dumps() for standards-compliant output."""
        bib_data = entry["bib_data"]
        entry_type = bib_data.get("ENTRYTYPE", "article")
        entry_id = bib_data.get("ID", entry["bib_key"])

        record = {"ENTRYTYPE": entry_type, "ID": entry_id}
        for key, value in bib_data.items():
            if key not in ("ENTRYTYPE", "ID") and value:
                value_str = str(value)
                if key in (
                    "author",
                    "title",
                    "journal",
                    "publisher",
                    "note",
                    "booktitle",
                    "series",
                    "address",
                    "howpublished",
                    "abstract",
                    "editor",
                ):
                    record[key] = self._escape_latex_chars(value_str)
                else:
                    record[key] = value_str.strip("{}")

        db = bibtexparser.bibdatabase.BibDatabase()
        db.entries = [record]
        writer = bibtexparser.bwriter.BibTexWriter()
        writer.indent = "  "
        return str(bibtexparser.dumps(db, writer)).strip()
