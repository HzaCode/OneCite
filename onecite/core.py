#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OneCite Core Engine - 4-Stage Processing Pipeline
"""

import re
import os
import json
import logging
import yaml
from typing import List, Dict, Optional, Union, Any, Callable, TypedDict
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import bibtexparser
from thefuzz import fuzz
try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

from .exceptions import ValidationError, ParseError, ResolverError


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


class CompletedEntry(TypedDict, total=False):
    """Stage 3: Completed Entry"""
    id: int
    doi: str
    status: str  # 'completed', 'enrichment_failed'
    bib_key: str
    bib_data: Dict[str, Any]


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
                ``onecite/templates/`` directory is used.
        """
        self.logger = logging.getLogger(__name__)
        if templates_dir is None:
            self.templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
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
            return self._get_default_template()
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = yaml.safe_load(f)
            self.logger.info(f"Successfully loaded template: {template_name}")
            return template
        except Exception as e:
            self.logger.error(f"Failed to load template {template_name}: {str(e)}")
            return self._get_default_template()
    
    def _get_default_template(self) -> Dict[str, Any]:
        """Return default journal_article template"""
        return {
            'name': 'journal_article_full',
            'entry_type': '@article',
            'fields': [
                {'name': 'author', 'required': True},
                {'name': 'title', 'required': True},
                {'name': 'journal', 'required': True},
                {'name': 'year', 'required': True},
                {'name': 'volume', 'required': False},
                {'name': 'number', 'required': False},
                {'name': 'pages', 'required': False},
                {'name': 'publisher', 'required': False},
                {'name': 'doi', 'required': False},
            ]
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
    
    def process(self, input_content: str, input_type: str, template_name: str,
                output_format: str, interactive_callback: Callable[[List[Dict]], int]) -> Dict[str, Any]:
        """Run all four pipeline stages and return results with a report.

        Args:
            input_content: The raw text or BibTeX content to process.
            input_type: Format of *input_content* — ``"txt"`` for
                plain-text references or ``"bib"`` for BibTeX.
            template_name: Name of the YAML template that controls
                which fields are collected (e.g.
                ``"journal_article_full"``).
            output_format: Output format. Only ``"bibtex"`` is
                supported; any other value raises ``FormatError``.
            interactive_callback: A callable that receives a list of
                candidate dictionaries and returns the index of the
                selected candidate.

        Returns:
            A dictionary with two keys:

            * ``results`` — a list of formatted citation strings.
            * ``report`` — a dict containing ``total``, ``succeeded``,
              and ``failed_entries``.
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


def process_references(
    input_content: str,
    input_type: str,
    template_name: str,
    output_format: str,
    interactive_callback: Callable[[List[Dict]], int],
    use_google_scholar: bool = False,
) -> Dict[str, Any]:
    """Process references and return formatted citations with a report.

    This is the main public API entry point.  It creates a
    :class:`PipelineController` and runs the full 4-stage pipeline.

    Args:
        input_content: The raw text or BibTeX content to process.
        input_type: Format of *input_content* — ``"txt"`` or ``"bib"``.
        template_name: Name of the YAML template (e.g.
            ``"journal_article_full"``).
        output_format: Output format. Only ``"bibtex"`` is supported;
            any other value raises ``FormatError``.
        interactive_callback: A callable that receives a list of
            candidate dictionaries and returns the index of the selected
            candidate.

    Returns:
        A dictionary with two keys:

        * ``results`` — a list of formatted citation strings.
        * ``report`` — a dict with ``total``, ``succeeded``, and
          ``failed_entries``.

    Raises:
        ValidationError: If the input content is empty or invalid.
        ParseError: If the input cannot be parsed.
        ResolverError: If no data source can resolve a reference.
    """
    if not input_content or not input_content.strip():
        raise ValidationError("input_content must not be empty.")
    pipeline = PipelineController(use_google_scholar=use_google_scholar)
    return pipeline.process(input_content, input_type, template_name, output_format, interactive_callback)
