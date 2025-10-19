#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OneCite Core Engine - 4-Stage Processing Pipeline
Core processing engine implemented strictly according to requirements
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
from scholarly import scholarly

from .exceptions import ValidationError, ParseError, ResolverError


# Data structure definitions (according to requirement document section 5)
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
    """Template Loader - Responsible for reading and parsing YAML template files"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        if templates_dir is None:
            # Default template directory
            self.templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        else:
            self.templates_dir = templates_dir
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load specified YAML template"""
        template_path = os.path.join(self.templates_dir, f"{template_name}.yaml")
        
        if not os.path.exists(template_path):
            # If template doesn't exist, create default template
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
    """Main Pipeline Controller - Manages the flow of four stages"""
    
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
        """
        Execute complete 4-stage processing pipeline
        
        Args:
            input_content: Input content
            input_type: Input type
            template_name: Template name
            output_format: Output format
            interactive_callback: Interactive callback function
        
        Returns:
            Processing results and report
        """
        self.logger.info("Starting OneCite processing pipeline")
        
        try:
            # Load template
            template = self.template_loader.load_template(template_name)
            
            # Stage 1: Parse
            raw_entries = self.parser.parse(input_content, input_type)
            
            # Stage 2: Identify
            identified_entries = self.identifier.identify(raw_entries, interactive_callback)
            
            # Stage 3: Enrich (pass raw_entries to preserve original fields)
            completed_entries = self.enricher.enrich(identified_entries, template, raw_entries)
            
            # Stage 4: Format
            result = self.formatter.format(completed_entries, output_format)
            
            self.logger.info("OneCite processing pipeline completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Processing pipeline execution failed: {str(e)}")
            raise


# Main API interface (according to requirement document section 6)
def process_references(
    input_content: str,
    input_type: str,
    template_name: str,
    output_format: str,
    interactive_callback: Callable[[List[Dict]], int]
) -> Dict[str, Any]:
    """
    OneCite core processing function
    
    Args:
        input_content: Complete string containing references
        input_type: Input type ('txt' or 'bib')
        template_name: Template name to use
        output_format: Final output format ('bibtex', 'apa', etc.)
        interactive_callback: A callback function to handle ambiguous matching selection
                              It receives a candidate list and should return user's choice index
    
    Returns:
        A dictionary containing processing results and report
        {
            "results": List[str], # List of formatted citation strings
            "report": {
                "total": int,
                "succeeded": int,
                "failed_entries": List[Dict]
            }
        }
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create pipeline controller and execute processing with intelligent search strategy
    pipeline = PipelineController(use_google_scholar=False)  # Will auto-fallback when needed
    return pipeline.process(input_content, input_type, template_name, output_format, interactive_callback)
