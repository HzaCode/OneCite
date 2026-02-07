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
    """Loads YAML template files."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        if templates_dir is None:
            self.templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        else:
            self.templates_dir = templates_dir
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load a YAML template by name, falling back to defaults."""
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
                {'name': 'volume', 'required': False, 'source_priority': ['crossref_api', 'user_prompt']},
                {'name': 'number', 'required': False, 'source_priority': ['crossref_api', 'user_prompt']},
                {'name': 'pages', 'required': False, 'source_priority': ['crossref_api', 'google_scholar_scraper']},
                {'name': 'publisher', 'required': False, 'source_priority': ['crossref_api', 'user_prompt']},
                {'name': 'doi', 'required': False, 'source_priority': ['crossref_api']},
            ]
        }


class PipelineController:
    """Runs the 4-stage pipeline: Parse -> Identify -> Enrich -> Format."""
    
    def __init__(self, use_google_scholar: bool = False):
        self.logger = logging.getLogger(__name__)
        from .pipeline import ParserModule, IdentifierModule, EnricherModule, FormatterModule
        
        self.template_loader = TemplateLoader()
        self.parser = ParserModule()
        self.identifier = IdentifierModule(use_google_scholar=use_google_scholar)
        self.enricher = EnricherModule(use_google_scholar=use_google_scholar)
        self.formatter = FormatterModule()
    
    def process(self, input_content: str, input_type: str, template_name: str,
                output_format: str, interactive_callback: Callable[[List[Dict]], int]) -> Dict[str, Any]:
        """Run all four stages and return results with a report."""
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
    interactive_callback: Callable[[List[Dict]], int]
) -> Dict[str, Any]:
    """Process references and return formatted citations with a report."""
    pipeline = PipelineController(use_google_scholar=False)
    return pipeline.process(input_content, input_type, template_name, output_format, interactive_callback)
