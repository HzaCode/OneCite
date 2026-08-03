#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OneCite Core Engine - 4-Stage Processing Pipeline
"""

import os
import logging
import yaml
from typing import List, Dict, Optional, Any, Callable, TypedDict

import requests  # noqa: F401 - kept as a stable patch target for tests and callers.

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

from .exceptions import ValidationError


class RawEntry(TypedDict, total=False):
    """Stage 1: Raw Entry"""

    id: int
    raw_text: str
    doi: Optional[str]
    url: Optional[str]
    query_string: Optional[str]
    original_entry: Optional[Dict[str, Any]]  # Preserve original BibTeX entry fields


class IdentifiedEntry(TypedDict, total=False):
    """Stage 2: Identified Entry"""

    id: int
    raw_text: str
    doi: Optional[str]
    arxiv_id: Optional[str]  # arXiv identifier
    url: Optional[str]  # Conference or other URL
    metadata: Optional[Dict[str, Any]]  # Additional metadata from various sources
    status: str  # 'identified', 'identification_failed'
    warnings: List[Dict[str, Any]]  # Non-blocking review warnings (e.g. text/DOI mismatch)
    failure_reason: str  # Why identification failed (e.g. 'doi_not_found', 'source_error')


class CompletedEntry(TypedDict, total=False):
    """Stage 3: Completed Entry"""

    id: int
    doi: str
    status: str  # 'completed', 'identification_failed', 'enrichment_failed'
    bib_key: str
    bib_data: Dict[str, Any]
    warnings: List[Dict[str, Any]]  # Non-blocking review warnings carried into the report
    raw_text: str  # Original input text, carried through for auditable failure reports
    failure_reason: str  # Why the entry failed (stage-specific reason code)


class TemplateLoader:
    """Loads YAML template files that provide fallback BibTeX entry types.

    Templates are used when auto-detection cannot determine the entry type
    from metadata. They specify which entry_type (e.g. @article, @book)
    to use as a fallback and which fields are expected.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize the template loader.

        Args:
            templates_dir: Path to a directory containing YAML template
                files.  When ``None`` (the default), the built-in
                ``src/onecite/templates/`` directory is used in a source checkout.
        """
        self.logger = logging.getLogger(__name__)
        if templates_dir is None:
            self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        else:
            self.templates_dir = templates_dir

    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load a YAML template by name, falling back to defaults.

        Args:
            template_name: The stem name of the template file (without
                the ``.yaml`` extension), e.g. ``"journal_article_full"``.

        Returns:
            A dictionary describing the template with keys ``name``,
            ``entry_type``, and ``fields``. The template provides a
            fallback entry type when auto-detection is inconclusive.
        """
        template_path = os.path.join(self.templates_dir, f"{template_name}.yaml")

        if not os.path.exists(template_path):
            self.logger.warning(
                "Template %r not found in %s; falling back to the default "
                "journal_article_full preset.",
                template_name,
                self.templates_dir,
            )
            return self._get_default_template()

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template: Dict[str, Any] = yaml.safe_load(f)
            self.logger.info(f"Successfully loaded template: {template_name}")
            return template
        except Exception as e:
            self.logger.error(f"Failed to load template {template_name}: {str(e)}")
            return self._get_default_template()

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return metadata for the configured YAML template directory.

        Returns:
            A list of dictionaries sorted by template name. Each item
            includes the template ``name``, fallback ``entry_type``,
            ``required_fields``, and ``optional_fields``.
        """
        templates: List[Dict[str, Any]] = []
        if not os.path.isdir(self.templates_dir):
            return templates

        for filename in sorted(os.listdir(self.templates_dir)):
            if not filename.endswith((".yaml", ".yml")):
                continue

            template_path = os.path.join(self.templates_dir, filename)
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    template = yaml.safe_load(f) or {}
            except Exception as e:
                self.logger.warning("Skipping unreadable template %s: %s", filename, e)
                continue

            fields = template.get("fields", [])
            required_fields = [
                field.get("name")
                for field in fields
                if field.get("name") and field.get("required") is True
            ]
            optional_fields = [
                field.get("name")
                for field in fields
                if field.get("name") and field.get("required") is not True
            ]
            templates.append(
                {
                    "name": template.get("name") or os.path.splitext(filename)[0],
                    "entry_type": template.get("entry_type", ""),
                    "required_fields": required_fields,
                    "optional_fields": optional_fields,
                }
            )

        return sorted(templates, key=lambda item: item["name"])

    def _get_default_template(self) -> Dict[str, Any]:
        """Return default journal_article template"""
        return {
            "name": "journal_article_full",
            "entry_type": "@article",
            "fields": [
                {"name": "author", "required": True},
                {"name": "title", "required": True},
                {"name": "journal", "required": True},
                {"name": "year", "required": True},
                {"name": "volume", "required": False},
                {"name": "number", "required": False},
                {"name": "pages", "required": False},
                {"name": "publisher", "required": False},
                {"name": "doi", "required": False},
            ],
        }


class PipelineController:
    """Runs the 4-stage pipeline: Parse -> Identify -> Enrich -> Format."""

    def __init__(self, use_google_scholar: bool = False):
        """Initialize the pipeline controller.

        Args:
            use_google_scholar: If ``True``, enable Google Scholar as an
                additional data source for identification and enrichment.
                Requires the optional ``scholarly`` package.  Defaults to
                ``False``.
        """
        self.logger = logging.getLogger(__name__)
        from .pipeline import ParserModule, IdentifierModule, EnricherModule, FormatterModule

        self.template_loader = TemplateLoader()
        self.parser = ParserModule()
        self.identifier = IdentifierModule(use_google_scholar=use_google_scholar)
        self.enricher = EnricherModule(use_google_scholar=use_google_scholar)
        self.formatter = FormatterModule()

    def process(
        self,
        input_content: str,
        input_type: str,
        template_name: str,
        output_format: str,
        interactive_callback: Optional[Callable[[List[Dict]], int]] = None,
    ) -> Dict[str, Any]:
        """Run all four pipeline stages and return results with a report.

        Args:
            input_content: The raw text or BibTeX content to process.
            input_type: Format of *input_content* — ``"txt"`` for
                plain-text references or ``"bib"`` for BibTeX.
            template_name: Name of the YAML template that controls
                which fields are collected (e.g.
                ``"journal_article_full"``).
            output_format: Output format. ``"bibtex"`` or
                ``"csl-json"``; any other value raises ``FormatError``.
            interactive_callback: Accepted for backward compatibility and
                never invoked — ``process`` is strictly non-interactive
                and fail-closed; candidate selection for ambiguous
                references lives in :func:`suggest_references`.

        Returns:
            A dictionary with two keys:

            * ``results`` — a list of formatted citation strings.
            * ``report`` — a dict containing ``total``, ``succeeded``,
              ``failed_entries``, and ``warnings``.
        """
        self.logger.info("Starting OneCite processing pipeline")

        try:
            template = self.template_loader.load_template(template_name)
            raw_entries = self.parser.parse(input_content, input_type)
            identified_entries = self.identifier.identify(raw_entries, interactive_callback)
            completed_entries = self.enricher.enrich(identified_entries, template, raw_entries)
            result = self.formatter.format(completed_entries, output_format)

            self.logger.info("OneCite processing pipeline completed")
            return result

        except Exception as e:
            self.logger.error(f"Processing pipeline execution failed: {str(e)}")
            raise

    def suggest(
        self,
        input_content: str,
        input_type: str,
        limit: int = 5,
        audit_trace: bool = False,
    ) -> Dict[str, Any]:
        """Return candidate matches without producing resolved BibTeX."""
        self.logger.info("Starting OneCite suggestion pipeline")
        raw_entries = self.parser.parse(input_content, input_type)
        suggestions = [
            self.identifier.suggest(entry, limit=limit, audit_trace=audit_trace)
            for entry in raw_entries
        ]
        with_candidates = sum(1 for item in suggestions if item["candidates"])
        return {
            "suggestions": suggestions,
            "report": {
                "total": len(suggestions),
                "with_candidates": with_candidates,
                "without_candidates": len(suggestions) - with_candidates,
            },
        }


def process_references(
    input_content: str,
    input_type: str,
    template_name: str,
    output_format: str,
    interactive_callback: Optional[Callable[[List[Dict]], int]] = None,
) -> Dict[str, Any]:
    """Process references and return formatted citations with a report.

    This is the main public API entry point.  It creates a
    :class:`PipelineController` and runs the full 4-stage pipeline.
    Processing is strictly non-interactive and fail-closed: entries
    without a verifiable strong identifier stay unresolved and are
    reported, never guessed.

    Args:
        input_content: The raw text or BibTeX content to process.
        input_type: Format of *input_content* — ``"txt"`` or ``"bib"``.
        template_name: Name of the YAML template (e.g.
            ``"journal_article_full"``).
        output_format: Output format. ``"bibtex"`` or ``"csl-json"``;
            any other value raises ``FormatError``.
        interactive_callback: Accepted for backward compatibility and
            never invoked; candidate selection for ambiguous references
            lives in :func:`suggest_references`.

    Returns:
        A dictionary with two keys:

        * ``results`` — a list of formatted citation strings.
        * ``report`` — a dict with ``total``, ``succeeded``,
          ``failed_entries``, and ``warnings`` (non-blocking review
          warnings, e.g. when input text disagrees with the resolved DOI's
          metadata).

    Raises:
        ValidationError: If the input content is empty or invalid.
        ParseError: If the input cannot be parsed.
        ResolverError: If no data source can resolve a reference.
    """
    if not input_content or not input_content.strip():
        raise ValidationError("input_content must not be empty.")
    pipeline = PipelineController()
    return pipeline.process(
        input_content, input_type, template_name, output_format, interactive_callback
    )


def suggest_references(
    input_content: str,
    input_type: str = "txt",
    limit: int = 5,
    use_google_scholar: bool = False,
    audit_trace: bool = False,
) -> Dict[str, Any]:
    """Return candidate citation matches without resolving to BibTeX.

    ``audit_trace`` is intended for provenance-locked evaluation only.  When
    true, the response retains private source/scoring positions; normal callers
    and CLI output keep the existing public candidate surface.
    """
    if not input_content or not input_content.strip():
        raise ValidationError("input_content must not be empty.")
    pipeline = PipelineController(use_google_scholar=use_google_scholar)
    return pipeline.suggest(input_content, input_type, limit=limit, audit_trace=audit_trace)
