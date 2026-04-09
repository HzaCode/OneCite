# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""OneCite 4-stage processing pipeline."""

import re
import os
import logging
import time
from typing import List, Dict, Optional, Callable, Any
import requests
from bs4 import BeautifulSoup
import bibtexparser
from thefuzz import fuzz
try:
    from scholarly import scholarly
except ImportError:
    scholarly = None
from html import unescape

from .core import RawEntry, IdentifiedEntry, CompletedEntry
from .exceptions import ParseError, ResolverError, ValidationError, FormatError
import urllib.parse


def _safe_year(date_obj):
    """Safely extract year from a CrossRef date object like {'date-parts': [[2015, 3, 1]]}."""
    if not date_obj:
        return None
    parts = date_obj.get('date-parts', [])
    if parts and isinstance(parts, list) and len(parts) > 0:
        inner = parts[0]
        if isinstance(inner, list) and len(inner) > 0:
            return inner[0]
    return None


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
        
        if input_type.lower() == 'bib':
            return self._parse_bibtex(input_content)
        elif input_type.lower() == 'txt':
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
                    'id': i,
                    'raw_text': str(entry),
                    'doi': entry.get('doi'),
                    'url': entry.get('url'),
                    'query_string': None,
                    'original_entry': original_entry
                }
                
                # If no DOI is available, generate query string
                if not raw_entry['doi']:
                    query_parts = []
                    if 'title' in entry:
                        query_parts.append(entry['title'])
                    if 'author' in entry:
                        query_parts.append(entry['author'])
                    if 'year' in entry:
                        query_parts.append(entry['year'])
                    raw_entry['query_string'] = ' '.join(query_parts)
                
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
        text_blocks = text_content.split('\n\n')
        
        for i, block in enumerate(text_blocks):
            block = block.strip()
            if not block:
                continue
            
            raw_entry: RawEntry = {
                'id': i,
                'raw_text': block,
                'doi': None,
                'url': None,
                'query_string': None
            }
            
            doi_match = re.search(r'10\.\d{4,}/[^\s,}]+', block)
            if doi_match:
                raw_entry['doi'] = doi_match.group().rstrip('.,;:)]')
            else:
                # Try to find article ID patterns that might be convertible to DOI
                # Common patterns: e0000429, PMC123456, etc.
                article_id_match = re.search(r'\b[eE]\d{7}\b', block)  # PLOS style: e0000429
                if article_id_match:
                    article_id = article_id_match.group()
                    # Note potential PLOS article ID but don't assume specific journal
                    # Let Cross resolve the actual DOI during identification
                    self.logger.info(f"Entry {i} found potential PLOS article ID {article_id}, will attempt resolution via CrossRef")
                    if not raw_entry['query_string']:
                        raw_entry['query_string'] = block
            
            url_match = re.search(r'https?://[^\s]+', block)
            if url_match:
                raw_entry['url'] = url_match.group()
            
            # If no DOI or URL found, build a concise query string from title/author/year
            if not raw_entry['doi'] and not raw_entry['url']:
                # Check if block is a bare PMID (7-8 digits, optionally prefixed with "PMID:")
                if re.match(r'^(PMID:?\s*)?\d{7,8}$', block.strip(), re.IGNORECASE):
                    raw_entry['query_string'] = block.strip()
                else:
                    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
                    title_text = lines[0] if lines else block
                    authors_text = lines[1] if len(lines) > 1 else ''
                    year_match = re.search(r'(19|20)\d{2}', block)
                    year_text = year_match.group(0) if year_match else ''

                    query_parts: List[str] = []
                    if title_text:
                        query_parts.append(title_text)
                    if authors_text:
                        query_parts.append(authors_text)
                    if year_text:
                        query_parts.append(year_text)

                    raw_entry['query_string'] = ' '.join(query_parts) or block
            
            entries.append(raw_entry)
        
        self.logger.info(f"Successfully parsed {len(entries)} text entries")
        return entries


class IdentifierModule:
    """Stage 2: Identification and Standardization Module."""
    
    def __init__(self, use_google_scholar: bool = False):
        """Initialize the identifier module.

        Args:
            use_google_scholar: Enable Google Scholar lookups when
                ``True``.  Defaults to ``False``.
        """
        self.logger = logging.getLogger(__name__)
        self.crossref_base_url = "https://api.crossref.org/works"
        self.use_google_scholar = use_google_scholar
        self.github_api_base = "https://api.github.com"
        self.zenodo_api_base = "https://zenodo.org/api/records"
        self.base_search_url = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
        self.openaire_api_base = "https://api.openaire.eu/search/publications"
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.datacite_base = "https://api.datacite.org"
        
    
    def identify(self, raw_entries: List[RawEntry], 
                interactive_callback: Callable[[List[Dict]], int]) -> List[IdentifiedEntry]:
        """Identify and standardize entries, finding a DOI for each.

        Args:
            raw_entries: List of raw entries produced by
                :meth:`ParserModule.parse`.
            interactive_callback: A callable that receives a list of
                candidate dictionaries and returns the index of the
                selected candidate.

        Returns:
            A list of :class:`IdentifiedEntry` dictionaries.
        """
        self.logger.info(f"Starting to identify {len(raw_entries)} entries")
        identified_entries = []
        
        for entry in raw_entries:
            identified_entry = self._identify_single_entry(entry, interactive_callback)
            identified_entries.append(identified_entry)
        
        successful_count = sum(1 for e in identified_entries if e['status'] == 'identified')
        self.logger.info(f"Identification completed: {successful_count}/{len(identified_entries)} entries successfully identified")
        
        return identified_entries
    
    def _identify_single_entry(self, raw_entry: RawEntry, 
                              interactive_callback: Callable[[List[Dict]], int]) -> IdentifiedEntry:
        """Identify a single entry"""
        identified_entry: IdentifiedEntry = {
            'id': raw_entry['id'],
            'raw_text': raw_entry['raw_text'],
            'doi': None,
            'arxiv_id': None,
            'url': None,
            'metadata': {},
            'status': 'identification_failed'
        }
        
        # If valid DOI already exists, verify it against Crossref API
        if raw_entry.get('doi'):
            if self._validate_doi(raw_entry['doi']):
                real_metadata = self._verify_doi_and_get_metadata(raw_entry['doi'])
                if real_metadata:
                    text_without_doi = raw_entry['raw_text'].replace(raw_entry['doi'], '').strip()
                    is_doi_only = len(text_without_doi) < 10  # Less than 10 chars means mostly just DOI
                    
                    if is_doi_only:
                        self.logger.info(f"Entry {raw_entry['id']} is DOI-only, accepting without consistency check")
                        identified_entry['doi'] = raw_entry['doi']
                        identified_entry['metadata'] = real_metadata
                        identified_entry['status'] = 'identified'
                        return identified_entry
                    
                    # Compare user input with fetched metadata
                    consistency_score = self._check_doi_content_consistency(raw_entry['raw_text'], real_metadata)
                    
                    identified_entry['doi'] = raw_entry['doi']
                    identified_entry['metadata'] = real_metadata
                    identified_entry['metadata']['consistency_score'] = consistency_score
                    identified_entry['status'] = 'identified'
                    
                    if consistency_score < 70:
                        self.logger.warning(f"Entry {raw_entry['id']} DOI verified but content inconsistent (score: {consistency_score}). Possible generated fake reference.")
                        identified_entry['metadata']['warning'] = 'low_consistency'
                        
                        # Reject the reference if consistency score is too low
                        # But allow DOI-only entries to pass through
                        if consistency_score < 20 and len(raw_entry['raw_text'].strip()) > 20:
                            self.logger.error(f"Entry {raw_entry['id']} consistency score too low ({consistency_score}), marking as failed")
                            identified_entry['status'] = 'identification_failed'
                            return identified_entry
                    else:
                        self.logger.info(f"Entry {raw_entry['id']} DOI verified with good consistency (score: {consistency_score})")
                    
                    return identified_entry
                else:
                    self.logger.warning(f"Entry {raw_entry['id']} has valid DOI format but DOI does not exist: {raw_entry['doi']}")
                    # Continue to fuzzy search as fallback
        
        github_info = self._extract_github_info(raw_entry['raw_text'])
        if github_info:
            identified_entry['metadata'] = github_info
            identified_entry['url'] = github_info.get('url')
            identified_entry['status'] = 'identified'
            self.logger.info(f"Entry {raw_entry['id']} identified as GitHub repository: {github_info.get('repo')}")
            return identified_entry
        
        zenodo_info = self._extract_zenodo_info(raw_entry['raw_text'])
        if zenodo_info:
            identified_entry['doi'] = zenodo_info.get('doi')
            identified_entry['metadata'] = zenodo_info
            identified_entry['status'] = 'identified'
            self.logger.info(f"Entry {raw_entry['id']} identified as Zenodo dataset")
            return identified_entry
        
        thesis_info = self._detect_thesis(raw_entry['raw_text'])
        if thesis_info:
            identified_entry['metadata'] = thesis_info
            identified_entry['status'] = 'identified'
            self.logger.info(f"Entry {raw_entry['id']} identified as thesis")
            return identified_entry
        
        arxiv_id = self._extract_arxiv_id(raw_entry['raw_text'])
        if arxiv_id:
            identified_entry['arxiv_id'] = arxiv_id
            identified_entry['status'] = 'identified'
            self.logger.info(f"Entry {raw_entry['id']} has arXiv ID: {arxiv_id}")
            return identified_entry
        
        # Try to extract DOI or arXiv ID from URL
        if raw_entry.get('url'):
            if 'github.com' in raw_entry['url']:
                github_info = self._extract_github_info(raw_entry['url'])
                if github_info:
                    identified_entry['metadata'] = github_info
                    identified_entry['url'] = raw_entry['url']
                    identified_entry['status'] = 'identified'
                    self.logger.info(f"Entry {raw_entry['id']} identified as GitHub repository from URL: {github_info.get('repo')}")
                    return identified_entry
            
            if 'arxiv.org' in raw_entry['url']:
                arxiv_id = self._extract_arxiv_id_from_url(raw_entry['url'])
                if arxiv_id:
                    identified_entry['arxiv_id'] = arxiv_id
                    identified_entry['url'] = raw_entry['url']
                    identified_entry['status'] = 'identified'
                    self.logger.info(f"Entry {raw_entry['id']} extracted arXiv ID from URL: {arxiv_id}")
                    return identified_entry
            
            # For other URLs
            if 'github.com' not in raw_entry['url'] and 'arxiv.org' not in raw_entry['url']:
                # Try to extract DOI
                extracted_doi = self._extract_doi_from_url(raw_entry['url'])
                if extracted_doi:
                    identified_entry['doi'] = extracted_doi
                    identified_entry['status'] = 'identified'
                    self.logger.info(f"Entry {raw_entry['id']} extracted DOI from URL: {extracted_doi}")
                    return identified_entry
                
                # Try to extract metadata from PDF or HTML page
                url_metadata = self._extract_metadata_from_url(raw_entry['url'])
                if url_metadata:
                    identified_entry['metadata'] = url_metadata
                    identified_entry['status'] = 'identified'
                    identified_entry['url'] = raw_entry['url']
                    self.logger.info(f"Entry {raw_entry['id']} extracted metadata from URL")
                    return identified_entry
                
                identified_entry['url'] = raw_entry['url']
        
        # Fuzzy search
        if raw_entry.get('query_string'):
            return self._fuzzy_search(raw_entry, interactive_callback)
        
        self.logger.warning(f"Entry {raw_entry['id']} identification failed")
        return identified_entry
    
    def _validate_doi(self, doi: str) -> bool:
        """Validate DOI format"""
        doi_pattern = r'^10\.\d{4,}/.+'
        return bool(re.match(doi_pattern, doi))
    
    def _verify_doi_and_get_metadata(self, doi: str) -> Optional[Dict]:
        """Verify DOI exists in Crossref and get real metadata for comparison"""
        try:
            url = f"{self.crossref_base_url}/{doi}"
            headers = {'Accept': 'application/json'}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            work = data.get('message', {})
            
            real_metadata = {
                'source': 'crossref_verification',
                'doi': work.get('DOI'),
                'title': work.get('title', [''])[0] if work.get('title') else '',
                'authors': [f"{a.get('given', '')} {a.get('family', '')}" 
                          for a in work.get('author', [])],
                'year': _safe_year(work.get('published-print')) or _safe_year(work.get('published-online')),
                'journal': work.get('container-title', [''])[0] if work.get('container-title') else '',
                'volume': work.get('volume'),
                'number': work.get('issue'),
                'pages': work.get('page'),
                'publisher': work.get('publisher'),
                'citations': work.get('is-referenced-by-count', 0),
                'url': work.get('URL')
            }
            
            self.logger.info(f"DOI {doi} verified successfully in CrossRef")
            return real_metadata
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"DOI {doi} not found in CrossRef (404)")
                return None
            else:
                self.logger.error(f"HTTP error verifying DOI {doi}: {str(e)}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to verify DOI {doi}: {str(e)}")
            return None
    
    def _check_doi_content_consistency(self, user_input: str, real_metadata: Dict) -> float:
        """Check consistency between user input and real DOI metadata to detect generated fake references"""
        try:
            # Normalize user input
            user_input_lower = user_input.lower()
            
            real_title = real_metadata.get('title', '').lower()
            real_authors = [author.lower() for author in real_metadata.get('authors', [])]
            real_year = str(real_metadata.get('year', ''))
            real_journal = real_metadata.get('journal', '').lower()
            
            scores = []
            
            # Title consistency (most important)
            if real_title:
                title_score = max(
                    fuzz.ratio(user_input_lower, real_title),
                    fuzz.partial_ratio(user_input_lower, real_title),
                    fuzz.token_set_ratio(user_input_lower, real_title)
                )
                scores.append(('title', title_score, 0.4))  # 40% weight
            
            # Author consistency
            if real_authors:
                author_scores = []
                for real_author in real_authors:
                    author_score = max(
                        fuzz.partial_ratio(user_input_lower, real_author),
                        fuzz.token_set_ratio(user_input_lower, real_author)
                    )
                    author_scores.append(author_score)
                best_author_score = max(author_scores) if author_scores else 0
                scores.append(('author', best_author_score, 0.3))  # 30% weight
            
            # Year consistency
            if real_year and real_year in user_input:
                scores.append(('year', 100, 0.2))  # 20% weight
            elif real_year:
                scores.append(('year', 0, 0.2))
            
            # Journal consistency
            if real_journal:
                journal_score = max(
                    fuzz.partial_ratio(user_input_lower, real_journal),
                    fuzz.token_set_ratio(user_input_lower, real_journal)
                )
                scores.append(('journal', journal_score, 0.1))  # 10% weight
            
            if not scores:
                return 0.0
            
            total_weighted_score = sum(score * weight for _, score, weight in scores)
            total_weight = sum(weight for _, _, weight in scores)
            
            final_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
            
            score_details = {field: score for field, score, _ in scores}
            self.logger.info(f"DOI consistency check details: {score_details}, final: {final_score:.2f}")
            
            return round(final_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error in DOI content consistency check: {str(e)}")
            return 0.0
    
    def _extract_github_info(self, text: str) -> Optional[Dict]:
        """Extract GitHub repository information"""
        try:
            # Match GitHub URLs
            github_pattern = r'github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)'
            match = re.search(github_pattern, text, re.IGNORECASE)
            
            if match:
                owner = match.group(1)
                repo = match.group(2)
                # Remove any trailing punctuation or special chars
                repo = re.sub(r'[^a-zA-Z0-9_.-].*$', '', repo)
                
                url = f"{self.github_api_base}/repos/{owner}/{repo}"
                headers = {
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'OneCite/1.0'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    version = None
                    try:
                        tags_url = f"{self.github_api_base}/repos/{owner}/{repo}/tags"
                        tags_response = requests.get(tags_url, headers=headers, timeout=5)
                        if tags_response.status_code == 200:
                            tags = tags_response.json()
                            if tags and len(tags) > 0:
                                version = tags[0].get('name', '').lstrip('v')
                    except Exception:
                        pass
                    
                    return {
                        'source': 'github',
                        'type': 'software',
                        'is_software': True,
                        'repo': f"{owner}/{repo}",
                        'title': data.get('name', repo),
                        'description': data.get('description', ''),
                        'authors': [data.get('owner', {}).get('login', owner)],
                        'year': data.get('created_at', '')[:4] if data.get('created_at') else None,
                        'url': data.get('html_url', ''),
                        'version': version,
                        'publisher': 'GitHub',
                        'language': data.get('language', ''),
                        'stars': data.get('stargazers_count', 0)
                    }
                    
        except Exception as e:
            self.logger.warning(f"Failed to extract GitHub info: {str(e)}")
        
        return None
    
    def _extract_zenodo_info(self, text: str) -> Optional[Dict]:
        """Extract Zenodo/Figshare dataset information"""
        try:
            zenodo_pattern = r'10\.5281/zenodo\.(\d+)'
            match = re.search(zenodo_pattern, text)
            
            if match:
                zenodo_id = match.group(1)
                doi = f"10.5281/zenodo.{zenodo_id}"
                
                url = f"https://zenodo.org/api/records/{zenodo_id}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    metadata = data.get('metadata', {})
                    
                    return {
                        'source': 'zenodo',
                        'type': 'dataset',
                        'is_dataset': True,
                        'doi': doi,
                        'title': metadata.get('title', ''),
                        'authors': [creator.get('name', '') for creator in metadata.get('creators', [])],
                        'year': metadata.get('publication_date', '')[:4] if metadata.get('publication_date') else None,
                        'publisher': 'Zenodo',
                        'url': f"https://zenodo.org/record/{zenodo_id}",
                        'version': metadata.get('version', ''),
                        'resource_type': metadata.get('resource_type', {}).get('type', 'dataset')
                    }
            
            figshare_pattern = r'10\.6084/m9\.figshare\.(\d+)'
            match = re.search(figshare_pattern, text)
            
            if match:
                doi = match.group(0)
                return {
                    'source': 'figshare',
                    'type': 'dataset',
                    'is_dataset': True,
                    'doi': doi,
                    'publisher': 'Figshare',
                    'url': f"https://doi.org/{doi}"
                }
            
            # DataCite DOIs often start with specific prefixes
            datacite_patterns = [
                r'10\.5061/',  # Dryad
                r'10\.6078/',  # DataONE
                r'10\.7910/',  # DVN/Dataverse
            ]
            
            for pattern in datacite_patterns:
                match = re.search(pattern + r'[^\s,}]+', text)
                if match:
                    doi = match.group(0)
                    datacite_info = self._query_datacite(doi)
                    if datacite_info:
                        return datacite_info
            
        except Exception as e:
            self.logger.warning(f"Failed to extract Zenodo/dataset info: {str(e)}")
        
        return None
    
    def _query_datacite(self, doi: str) -> Optional[Dict]:
        """Query DataCite API for dataset metadata"""
        try:
            url = f"{self.datacite_base}/dois/{doi}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                attributes = data.get('data', {}).get('attributes', {})
                
                creators = attributes.get('creators', [])
                authors = [c.get('name', '') for c in creators if c.get('name')]
                
                pub_year = attributes.get('publicationYear')
                
                return {
                    'source': 'datacite',
                    'type': 'dataset',
                    'is_dataset': True,
                    'doi': doi,
                    'title': attributes.get('titles', [{}])[0].get('title', '') if attributes.get('titles') else '',
                    'authors': authors,
                    'year': pub_year,
                    'publisher': attributes.get('publisher', 'DataCite'),
                    'url': attributes.get('url', f"https://doi.org/{doi}"),
                    'resource_type': attributes.get('types', {}).get('resourceTypeGeneral', 'Dataset')
                }
                
        except Exception as e:
            self.logger.warning(f"DataCite query failed for {doi}: {str(e)}")
        
        return None
    
    def _detect_thesis(self, text: str) -> Optional[Dict]:
        """Detect and search for thesis/dissertation"""
        try:
            text_lower = text.lower()
            
            thesis_keywords = [
                'phd thesis', 'ph.d. thesis', 'doctoral thesis', 'dissertation',
                'master thesis', "master's thesis", 'msc thesis', 'm.s. thesis'
            ]
            
            is_thesis = any(keyword in text_lower for keyword in thesis_keywords)
            
            if not is_thesis:
                return None
            
            # Determine thesis type
            is_phd = any(kw in text_lower for kw in ['phd', 'ph.d.', 'doctoral', 'dissertation'])
            thesis_type = 'phdthesis' if is_phd else 'mastersthesis'
            
            # Pattern: Author (Year). Title. Type. University.
            author_match = re.match(r'^([^(]+?)\s*\(', text)
            author = author_match.group(1).strip() if author_match else None
            
            year_match = re.search(r'\((\d{4})\)', text)
            year = int(year_match.group(1)) if year_match else None
            
            title = None
            title_pattern = r'\(\d{4}\)\.\s*(.+?)\.\s*(?:PhD|Ph\.D\.|Master|Doctoral|Dissertation)'
            title_match = re.search(title_pattern, text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
            else:
                # Fallback: extract text after year
                parts = text.split(')')
                if len(parts) > 1:
                    rest = parts[1].strip().lstrip('.')
                    # Take text before thesis keyword
                    for keyword in thesis_keywords:
                        if keyword in rest.lower():
                            title = rest.split(keyword)[0].strip().rstrip('.')
                            break
                    if not title:
                        title = rest.split('.')[0].strip()
            
            # Try to extract university/school
            university_patterns = [
                r'(?:PhD|Ph\.D\.|Master|Doctoral|Dissertation).*?([A-Z][^.]*?University[^.]*?)\.?\s*$',
                r'([A-Z][^.]*?University[^.]*?)\.?\s*$',
            ]
            
            school = None
            for pattern in university_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    school = match.group(1).strip().rstrip('.')
                    break
            
            if title and len(title) > 10:
                # Try external providerRE first (better for European theses)
                openaire_metadata = self._search_openaire_for_thesis(title, year)
                if openaire_metadata:
                    openaire_metadata['thesis_type'] = thesis_type
                    openaire_metadata['is_thesis'] = True
                    if author:
                        openaire_metadata['authors'] = [author]
                    if school:
                        openaire_metadata['school'] = school
                    return openaire_metadata
                
                # Fallback to BASE
                base_metadata = self._search_base_for_thesis(title, year)
                if base_metadata:
                    base_metadata['thesis_type'] = thesis_type
                    base_metadata['is_thesis'] = True
                    if author:
                        base_metadata['authors'] = [author]
                    if school:
                        base_metadata['school'] = school
                    return base_metadata
            
            # Fallback: create basic metadata from extraction (only if we have a title)
            if not title:
                return None
            result = {
                'source': 'manual',
                'type': thesis_type,
                'is_thesis': True,
                'thesis_type': thesis_type,
                'title': title,
                'authors': [author] if author else [],
                'year': year,
            }
            if school:
                result['school'] = school
            return result
            
        except Exception as e:
            self.logger.warning(f"Failed to detect thesis: {str(e)}")
        
        return None
    
    def _search_base_for_thesis(self, query: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search BASE (Bielefeld Academic Search Engine) for thesis"""
        try:
            # Clean query
            query_clean = re.sub(r'\b(phd|ph\.d\.|thesis|dissertation)\b', '', query, flags=re.IGNORECASE).strip()
            
            base_query = f'dccoll:ftthesis {query_clean}'
            if year:
                base_query += f' dcyear:{year}'
            
            params = {
                'func': 'PerformSearch',
                'query': base_query,
                'hits': 3,
                'format': 'json'
            }
            
            response = requests.get(self.base_search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get('response', {}).get('docs', [])
                
                if docs:
                    doc = docs[0]
                    
                    authors = doc.get('dcauthor', [])
                    if isinstance(authors, str):
                        authors = [authors]
                    
                    return {
                        'source': 'base_search',
                        'title': doc.get('dctitle', [''])[0] if isinstance(doc.get('dctitle'), list) else doc.get('dctitle', ''),
                        'authors': authors,
                        'year': doc.get('dcyear', [''])[0] if isinstance(doc.get('dcyear'), list) else doc.get('dcyear'),
                        'school': doc.get('dccreator', [''])[0] if isinstance(doc.get('dccreator'), list) else doc.get('dccreator', 'Unknown'),
                        'url': doc.get('dclink', [''])[0] if isinstance(doc.get('dclink'), list) else doc.get('dclink', ''),
                        'type': 'thesis'
                    }
            
        except Exception as e:
            self.logger.warning(f"BASE search for thesis failed: {str(e)}")
        
        return None
    
    def _search_openaire_for_thesis(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search external providerRE for thesis/dissertation"""
        try:
            query = f'"{title}"'
            if year:
                query += f' AND yearofacceptance exact "{year}"'
            
            params = {
                'title': title,
                'format': 'json',
                'size': 3,
                'type': 'publications',
                'publicationtype': 'Bachelor thesis OR Master thesis OR Doctoral thesis'
            }
            
            response = requests.get(self.openaire_api_base, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('response', {}).get('results', {}).get('result', [])
                
                if results:
                    # Take first result
                    result = results[0] if isinstance(results, list) else results
                    metadata_elem = result.get('metadata', {}).get('oaf:entity', {}).get('oaf:result', {})
                    
                    title_elem = metadata_elem.get('title', {})
                    if isinstance(title_elem, list):
                        title_text = title_elem[0].get('$', '') if title_elem else ''
                    else:
                        title_text = title_elem.get('$', '')
                    
                    creators = metadata_elem.get('creator', [])
                    if not isinstance(creators, list):
                        creators = [creators]
                    authors = [c.get('$', '') if isinstance(c, dict) else str(c) for c in creators if c]
                    
                    year_elem = metadata_elem.get('dateofacceptance', {})
                    year_text = year_elem.get('$', '')[:4] if isinstance(year_elem, dict) and year_elem.get('$') else None
                    
                    # Extract publisher (university)
                    publisher_elem = metadata_elem.get('publisher', {})
                    publisher = publisher_elem.get('$', 'Unknown University') if isinstance(publisher_elem, dict) else str(publisher_elem)
                    
                    url = None
                    children = result.get('metadata', {}).get('oaf:entity', {}).get('oaf:result', {}).get('children', {})
                    instances = children.get('instance', [])
                    if not isinstance(instances, list):
                        instances = [instances]
                    for instance in instances:
                        if isinstance(instance, dict) and instance.get('webresource'):
                            webres = instance['webresource']
                            if isinstance(webres, list):
                                url = webres[0].get('url', {}).get('$', '')
                            else:
                                url = webres.get('url', {}).get('$', '')
                            if url:
                                break
                    
                    if title_text:
                        return {
                            'source': 'openaire',
                            'title': title_text,
                            'authors': authors,
                            'year': year_text,
                            'school': publisher,
                            'url': url or '',
                            'type': 'thesis'
                        }
            
        except Exception as e:
            self.logger.warning(f"external providerRE search for thesis failed: {str(e)}")
        
        return None
    
    def _search_pubmed_by_id(self, pmid: str) -> Optional[Dict]:
        """Search PubMed by PMID"""
        try:
            url = f"{self.pubmed_base}/esummary.fcgi"
            params = {
                'db': 'pubmed',
                'id': pmid,
                'retmode': 'json'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            result = data.get('result', {}).get(pmid, {})
            
            if result and result.get('title'):
                doi = None
                article_ids = result.get('articleids', [])
                for aid in article_ids:
                    if aid.get('idtype') == 'doi':
                        doi = aid.get('value')
                        break
                
                authors = []
                for author in result.get('authors', []):
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
                
                return {
                    'source': 'pubmed',
                    'type': 'article',
                    'pmid': pmid,
                    'doi': doi,
                    'title': result.get('title', ''),
                    'authors': authors,
                    'journal': result.get('fulljournalname', result.get('source', '')),
                    'year': result.get('pubdate', '')[:4] if result.get('pubdate') else None,
                    'volume': result.get('volume'),
                    'issue': result.get('issue'),
                    'pages': result.get('pages'),
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                }
                
        except Exception as e:
            self.logger.warning(f"PubMed ID search failed: {str(e)}")
        
        return None
    
    def _search_pubmed(self, query: str, limit: int = 5) -> List[Dict]:
        """Search PubMed for medical literature"""
        try:
            # First, search for PMIDs
            search_url = f"{self.pubmed_base}/esearch.fcgi"
            params = {
                'db': 'pubmed',
                'term': query,
                'retmax': limit,
                'retmode': 'json'
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get('esearchresult', {}).get('idlist', [])
            
            if not pmids:
                return []
            
            results = []
            for pmid in pmids:
                result = self._search_pubmed_by_id(pmid)
                if result:
                    results.append(result)
            
            self.logger.info(f"PubMed search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.warning(f"PubMed search failed: {str(e)}")
            return []
    
    def _search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Semantic Scholar for academic papers"""
        try:
            url = f"{self.semantic_scholar_base}/paper/search"
            params = {
                'query': query,
                'limit': limit,
                'fields': 'title,authors,year,venue,citationCount,publicationDate,externalIds,journal,url'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                self.logger.debug("Semantic Scholar rate-limited (429); skipping for this query.")
                return []
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                
                results = []
                for paper in papers:
                    external_ids = paper.get('externalIds') or {}
                    doi = external_ids.get('DOI') if external_ids else None
                    arxiv_id = external_ids.get('ArXiv') if external_ids else None
                    
                    authors = []
                    author_list = paper.get('authors') or []
                    for author in author_list:
                        if author and isinstance(author, dict):
                            name = author.get('name', '')
                            if name:
                                authors.append(name)
                    
                    venue = paper.get('venue') or ''
                    if not venue:
                        journal_obj = paper.get('journal')
                        if journal_obj and isinstance(journal_obj, dict):
                            venue = journal_obj.get('name', '')
                    
                    paper_url = paper.get('url')
                    if not paper_url and paper.get('paperId'):
                        paper_url = f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"
                    
                    result = {
                        'source': 'semantic_scholar',
                        'doi': doi,
                        'arxiv_id': arxiv_id,
                        'title': paper.get('title', ''),
                        'authors': authors,
                        'year': paper.get('year'),
                        'journal': venue,
                        'citations': paper.get('citationCount', 0),
                        'url': paper_url,
                        'type': 'article'
                    }
                    
                    if result['title'] and result['authors']:
                        results.append(result)
                
                self.logger.info(f"Semantic Scholar search returned {len(results)} results")
                return results
            else:
                self.logger.warning(f"Semantic Scholar returned status code {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Semantic Scholar search failed: {str(e)}")
            return []
    
    def _extract_arxiv_id(self, text: str) -> Optional[str]:
        """Extract arXiv ID from text"""
        # Match both old (e.g., 1706.03762) and new (e.g., arxiv:1706.03762) formats
        arxiv_patterns = [
            r'arxiv[:\s]*(\d{4}\.\d{4,5})',  # New format
            r'\b(\d{4}\.\d{4,5})\b',  # Standalone ID
            r'arXiv:(\d{4}\.\d{4,5})',  # With arXiv prefix
        ]
        
        for pattern in arxiv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_arxiv_id_from_url(self, url: str) -> Optional[str]:
        """Extract arXiv ID from arXiv URL"""
        # Match patterns like https://arxiv.org/abs/1706.03762
        match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', url)
        if match:
            return match.group(1)
        return None
    
    def _extract_doi_from_url(self, url: str) -> Optional[str]:
        """Extract DOI from URL page. Prioritize meta tags and avoid extracting DOIs from reference sections."""
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'OneCite/1.0'}, stream=True)
            content_len = response.headers.get('content-length')
            if content_len and int(content_len) > 5 * 1024 * 1024:
                self.logger.warning(f"Skipping URL {url}: response too large ({content_len} bytes)")
                return None
            content = response.raw.read(5 * 1024 * 1024)
            soup = BeautifulSoup(content, 'html.parser')
            
            # 1. Look for DOI in meta tags (most reliable)
            doi_meta = soup.find('meta', attrs={'name': 'citation_doi'}) or \
                      soup.find('meta', attrs={'name': 'dc.identifier'}) or \
                      soup.find('meta', attrs={'property': 'citation_doi'})
            
            if doi_meta and 'content' in doi_meta.attrs:
                doi = doi_meta['content']
                if self._validate_doi(doi):
                    self.logger.info(f"Found DOI in meta tags: {doi}")
                    return doi
            
            # 2. Check schema.org structured data
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'identifier' in data:
                        identifier = data['identifier']
                        if isinstance(identifier, str) and self._validate_doi(identifier):
                            self.logger.info(f"Found DOI in structured data: {identifier}")
                            return identifier
                except Exception:
                    pass
            
            # 3. Limited search in main content only (exclude reference sections)
            # Remove known reference/citation sections to avoid false matches
            for ref_section in soup.find_all(['div', 'section', 'article'], 
                                            attrs={'class': re.compile(r'(reference|citation|bibliography)', re.IGNORECASE)}):
                ref_section.decompose()
            for ref_section in soup.find_all(['div', 'section', 'article'], 
                                            id=re.compile(r'(reference|citation|bibliography)', re.IGNORECASE)):
                ref_section.decompose()
            
            # Also remove common reference list elements
            for ref_list in soup.find_all(['ul', 'ol'], 
                                         attrs={'class': re.compile(r'(reference|citation)', re.IGNORECASE)}):
                ref_list.decompose()
            
            # Search in remaining main content area
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                # Look for DOI patterns, but be cautious
                content_text = main_content.get_text()
                doi_match = re.search(r'(?:doi:?\s*|https?://doi\.org/)?(10\.\d{4,}/[^\s"<>,}]+)', content_text, re.IGNORECASE)
                if doi_match:
                    doi = doi_match.group(1) if doi_match.lastindex >= 1 else doi_match.group(0)
                    # Clean up the DOI
                    doi = re.sub(r'^https?://doi\.org/', '', doi, flags=re.IGNORECASE)
                    doi = re.sub(r'^doi:?\s*', '', doi, flags=re.IGNORECASE)
                    
                    if self._validate_doi(doi):
                        self.logger.warning(f"Found DOI in page content (not meta tags): {doi}. May be less reliable.")
                        return doi
            
            # 4. If nothing found, return None (don't use full page text)
            self.logger.info(f"No reliable DOI found in URL: {url}")
            return None
                    
        except Exception as e:
            self.logger.warning(f"Failed to extract DOI from URL {url}: {str(e)}")
        
        return None
    
    def _extract_metadata_from_url(self, url: str) -> Optional[Dict]:
        """Extract metadata from PDF or HTML page"""
        try:
            response = requests.get(url, timeout=15, headers={'User-Agent': 'OneCite/1.0'}, stream=True)
            content_len = response.headers.get('content-length')
            if content_len and int(content_len) > 5 * 1024 * 1024:
                self.logger.warning(f"Skipping URL {url}: response too large ({content_len} bytes)")
                return None
            response._content = response.raw.read(5 * 1024 * 1024)
            response.raise_for_status()
            
            # Check if it's a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                return self._extract_from_pdf_content(response.content)
            else:
                return self._extract_from_html_content(response.content)
                
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from URL {url}: {str(e)}")
            return None
    
    def _extract_from_html_content(self, content: bytes) -> Optional[Dict]:
        """Extract metadata from HTML content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            metadata = {}
            
            # Look for academic metadata in meta tags
            meta_mappings = {
                'title': ['citation_title', 'dc.title', 'og:title'],
                'author': ['citation_author', 'dc.creator', 'author'],
                'journal': ['citation_journal_title', 'dc.source', 'citation_conference_title'],
                'year': ['citation_publication_date', 'citation_date', 'dc.date'],
                'abstract': ['citation_abstract', 'dc.description', 'description'],
                'volume': ['citation_volume'],
                'pages': ['citation_firstpage', 'citation_lastpage']
            }
            
            authors = []
            for field, tag_names in meta_mappings.items():
                for tag_name in tag_names:
                    metas = soup.find_all('meta', attrs={'name': tag_name}) + \
                           soup.find_all('meta', attrs={'property': tag_name})
                    
                    for meta in metas:
                        if meta.get('content'):
                            content_value = meta['content'].strip()
                            if not content_value:
                                continue
                                
                            if field == 'author':
                                authors.append(content_value)
                            elif field == 'year':
                                year_match = re.search(r'\b(19|20)\d{2}\b', content_value)
                                if year_match:
                                    metadata[field] = int(year_match.group())
                            elif field == 'journal':
                                # Don't overwrite if already found
                                if field not in metadata:
                                    metadata[field] = content_value
                            else:
                                metadata[field] = content_value
                            
                            # For non-author fields, break after finding first valid value
                            if field != 'author':
                                break
                    
                    # For non-author fields, break after finding value from any tag
                    if field != 'author' and field in metadata:
                        break
            
            # Process authors
            if authors:
                # Clean up author names and join them
                cleaned_authors = []
                for author in authors:
                    # Remove extra whitespace and common prefixes
                    author = re.sub(r'^\s*(by\s+)?', '', author, flags=re.IGNORECASE).strip()
                    if author and len(author) > 2:
                        cleaned_authors.append(author)
                
                if cleaned_authors:
                    metadata['author'] = ' and '.join(cleaned_authors)
            
            # If no title found, try page title
            if 'title' not in metadata:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()
                    # Clean up common title suffixes
                    title = re.sub(r'\s*[-|]\s*(PDF|Download|Paper|Abstract).*$', '', title, flags=re.IGNORECASE)
                    if len(title) > 10:
                        metadata['title'] = title
            
            # If still no authors, try to extract from page content
            if 'author' not in metadata:
                authors_from_content = self._extract_authors_from_content(soup)
                if authors_from_content:
                    metadata['author'] = authors_from_content
            
            # Extract year from title or content if not found
            if 'year' not in metadata:
                year_from_content = self._extract_year_from_content(soup, metadata.get('title', ''))
                if year_from_content:
                    metadata['year'] = year_from_content
            
            return metadata if len(metadata) >= 1 else None
            
        except Exception as e:
            self.logger.warning(f"Failed to extract from HTML: {str(e)}")
            return None
    
    def _extract_authors_from_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract authors from page content when meta tags are not available"""
        try:
            # Look for author-related elements
            author_selectors = [
                '[class*="author"]',
                '[class*="byline"]', 
                '[id*="author"]',
                '.authors',
                '.author-list'
            ]
            
            for selector in author_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text().strip()
                    if text and 10 <= len(text) <= 200:
                        # Clean up the text
                        text = re.sub(r'^\s*(authors?|by)\s*:?\s*', '', text, flags=re.IGNORECASE)
                        # Look for name patterns
                        if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', text):
                            return text
            
            # Try pattern matching in the full text
            page_text = soup.get_text()
            
            # Pattern 1: "By Author Name"
            by_pattern = r'[Bb]y\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)*)'
            match = re.search(by_pattern, page_text)
            if match:
                return match.group(1)
            
            # Pattern 2: "Authors: Name1, Name2"
            authors_pattern = r'[Aa]uthors?\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)'
            match = re.search(authors_pattern, page_text)
            if match:
                return match.group(1)
                
        except Exception as e:
            self.logger.warning(f"Failed to extract authors from content: {str(e)}")
        
        return None
    
    def _extract_year_from_content(self, soup: BeautifulSoup, title: str = '') -> Optional[int]:
        """Extract publication year from content"""
        try:
            # First try to find year in title
            if title:
                year_match = re.search(r'\b(19|20)\d{2}\b', title)
                if year_match:
                    return int(year_match.group())
            
            # Look for year in specific elements
            year_selectors = [
                '[class*="year"]',
                '[class*="date"]',
                '.publication-date',
                '.pub-date'
            ]
            
            for selector in year_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text()
                    year_match = re.search(r'\b(19|20)\d{2}\b', text)
                    if year_match:
                        return int(year_match.group())
            
            # Try to find year in the first few paragraphs
            paragraphs = soup.find_all('p')[:5]
            for p in paragraphs:
                text = p.get_text()
                year_match = re.search(r'\b(19|20)\d{2}\b', text)
                if year_match:
                    year = int(year_match.group())
                    # Only accept reasonable years for academic papers
                    if 1950 <= year <= 2030:
                        return year
                        
        except Exception as e:
            self.logger.warning(f"Failed to extract year from content: {str(e)}")
        
        return None
    
    def _extract_from_pdf_content(self, content: bytes) -> Optional[Dict]:
        """Extract metadata from PDF content"""
        try:
            import PyPDF2
            import io
            
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            metadata = {}
            
            # Extract from PDF metadata
            if pdf_reader.metadata:
                pdf_meta = pdf_reader.metadata
                if pdf_meta.get('/Title'):
                    title = str(pdf_meta['/Title']).strip()
                    if len(title) > 5:
                        metadata['title'] = title
                if pdf_meta.get('/Author'):
                    author = str(pdf_meta['/Author']).strip()
                    if len(author) > 3:
                        metadata['author'] = author
            
            # Extract from first page text
            if len(pdf_reader.pages) > 0:
                try:
                    first_page_text = pdf_reader.pages[0].extract_text()
                    if first_page_text:
                        lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
                        
                        # Try to find title (usually one of the first few lines)
                        if 'title' not in metadata:
                            for line in lines[:5]:
                                if 20 <= len(line) <= 200 and not line.isupper():
                                    # Skip lines that look like headers/footers
                                    if not re.search(r'(page|abstract|introduction|©|\d+)', line.lower()):
                                        metadata['title'] = line
                                        break
                        
                        # Try to extract year
                        year_match = re.search(r'\b(19|20)\d{2}\b', first_page_text)
                        if year_match:
                            metadata['year'] = int(year_match.group())
                            
                except Exception as e:
                    self.logger.warning(f"Failed to extract text from PDF: {str(e)}")
            
            return metadata if metadata else None
            
        except ImportError:
            self.logger.warning("PyPDF2 not available for PDF parsing")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to extract from PDF: {str(e)}")
            return None
    
    def _fuzzy_search(self, raw_entry: RawEntry, 
                     interactive_callback: Callable[[List[Dict]], int]) -> IdentifiedEntry:
        """Perform fuzzy search"""
        query_string = raw_entry['query_string']
        
        # Multi-source query with fallback
        candidates = []
        semantic_results = []  # Initialize to avoid UnboundLocalError
        
        # Check if query might be a PMID (PubMed ID)
        pmid_match = re.match(r'^(PMID:?\s*)?(\d{7,8})$', query_string.strip())
        if pmid_match:
            pmid = pmid_match.group(2)
            self.logger.info(f"Detected PubMed ID: {pmid}")
            pubmed_result = self._search_pubmed_by_id(pmid)
            if pubmed_result:
                return {
                    'id': raw_entry['id'],
                    'raw_text': raw_entry['raw_text'],
                    'doi': pubmed_result.get('doi'),
                    'arxiv_id': None,
                    'url': pubmed_result.get('url'),
                    'metadata': pubmed_result,
                    'status': 'identified'
                }
        
        # Check if it might be a book
        query_lower = query_string.lower()
        
        # === Strongest book indicators ===
        has_isbn = bool(re.search(r'isbn[:\s]*[\d\-xX]{10,17}', query_lower, re.IGNORECASE))  # ISBN-10 or ISBN-13
        has_editor = bool(re.search(r'\b(ed\.|eds\.|editor|editors|edited\s+by)\b', query_lower))  # Editor indicators
        
        # === Strong book indicators ===
        has_edition_number = bool(re.search(r'\d+(?:st|nd|rd|th)?\s+ed\.', query_lower))  # "2nd ed.", "3rd edition"
        has_press_publisher = bool(re.search(r'\b(mit|cambridge|oxford|springer|wiley|princeton)\s+press\b', query_lower))
        has_book_publisher = any(pub in query_lower for pub in ['wiley & sons', "o'reilly media", "o'reilly", 'addison-wesley', 'addison wesley'])
        has_publisher_location = bool(re.search(r'\b[A-Z][a-z]+,\s+(MA|NY|CA|UK):', query_string))  # "Cambridge, MA:" or "New York:"
        has_chapter = bool(re.search(r'\bchapter\s+\d+\b', query_lower))  # "Chapter 5"
        has_total_pages = bool(re.search(r'\b\d{2,4}\s+pp\.?\b', query_lower))  # "500 pp." (total pages)
        has_series = bool(re.search(r'\b(series|lecture notes)\b', query_lower))  # Book series
        
        # === Medium indicators ===
        mentions_edition = 'edition' in query_lower
        mentions_revised = any(word in query_lower for word in ['revised', 'updated', 'expanded'])
        
        # === Negative indicators (article/paper features) ===
        has_doi = bool(re.search(r'10\.\d{4,}/[^\s,}]+', query_string))
        has_journal_keywords = any(j in query_lower for j in ['journal of', 'proceedings of', 'conference on', 'transactions on', 'bulletin of', 'annals of'])
        has_volume_issue = bool(re.search(r'\b\d+\(\d+\)', query_string))  # Pattern like "83(8)" or "15(1)"
        has_article_pages = bool(re.search(r'\b\d{1,4}[-–]\d{1,4}\b', query_string)) and not has_total_pages  # "123-456" but not "pp. 1-500"
        has_article_number = bool(re.search(r'\barticle\s+(number|no\.?)\b', query_lower))
        
        # === Decision logic with priority ===
        if has_isbn or has_editor:
            is_likely_book = True  # ISBN or editor is definitive for books
            self.logger.info(f"Book indicators: ISBN={has_isbn}, Editor={has_editor}")
        elif has_doi or has_journal_keywords or (has_volume_issue and has_article_pages):
            is_likely_book = False  # Definitely an article/paper
        elif has_edition_number or has_press_publisher or has_book_publisher or has_publisher_location or has_chapter or has_series:
            is_likely_book = True  # Strong book signals
        elif mentions_edition and mentions_revised and not has_article_pages:
            is_likely_book = True  # Revised edition mention
        else:
            is_likely_book = False  # Default to article (safer)
        
        # === Route to the best API based on content type ===
        
        is_medical = any(keyword in query_lower for keyword in 
                        ['health', 'medical', 'clinical', 'patient', 'disease', 'treatment', 
                         'therapy', 'diagnosis', 'biology', 'gene', 'protein', 'cell', 
                         'epidemiology', 'public health'])
        
        if is_likely_book:
            # === Book route ===
            self.logger.info("Likely a book, trying Google Books API first")
            books_results = self._search_google_books(query_string)
            
            if books_results and len(books_results) > 0:
                books_results[0]['is_primary_google_books_match'] = True
            
            candidates.extend(books_results)
            crossref_results = self._search_crossref(query_string)
            candidates.extend(crossref_results)
            
        elif is_medical:
            # === Medical route ===
            self.logger.info("Detected medical content, prioritizing PubMed")
            pubmed_results = self._search_pubmed(query_string)
            candidates.extend(pubmed_results)
            
            # Also try Crossref (many medical journals indexed there too)
            crossref_results = self._search_crossref(query_string)
            candidates.extend(crossref_results)
            
            # Semantic Scholar is good for medical CS papers (e.g., medical imaging automation)
            if any(cs_kw in query_lower for cs_kw in ['neural', 'deep learning', 'machine learning', 'ai']):
                semantic_results = self._search_semantic_scholar(query_string)
                candidates.extend(semantic_results)
            
        else:
            # === General academic paper route ===
            # Try Cross first (fastest and most reliable)
            crossref_results = self._search_crossref(query_string)
            candidates.extend(crossref_results)
            
            # If CrossRef results are good, also check Semantic Scholar for enrichment
            # (Semantic Scholar provides better metadata: citations, influential citations, etc.)
            if len(crossref_results) > 0:
                semantic_results = self._search_semantic_scholar(query_string)
                candidates.extend(semantic_results)
                self.logger.info(f"CrossRef found {len(crossref_results)} results, also querying Semantic Scholar for enrichment")
            
            # If CrossRef found nothing or poor results, use fallbacks
            if len(crossref_results) == 0 or (crossref_results and max(c.get('citations', 0) for c in crossref_results) < 10):
                self.logger.info("CrossRef results insufficient, trying fallbacks")
                
                # Try Semantic Scholar as primary fallback
                if not semantic_results:  # If not already tried
                    semantic_results = self._search_semantic_scholar(query_string)
                    candidates.extend(semantic_results)
                
                # Google Scholar as last resort (if enabled)
                if self.use_google_scholar:
                    self.logger.info("Google Scholar enabled, searching...")
                    scholar_results = self._search_google_scholar(query_string)
                    candidates.extend(scholar_results)
                else:
                    self.logger.info("Google Scholar disabled by user, skipping")
        
        if not candidates:
            self.logger.warning(f"Entry {raw_entry['id']}: no candidate results found")
            return {
                'id': raw_entry['id'],
                'raw_text': raw_entry['raw_text'],
                'doi': None,
                'arxiv_id': None,
                'url': None,
                'metadata': {},
                'status': 'identification_failed'
            }
        
        scored_candidates = self._score_candidates(candidates, query_string)
        scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)

        best_candidate = scored_candidates[0]
        
        # For likely books, strongly prefer Google Books results if available
        if not is_likely_book:
            is_likely_book = any(pub in query_string.lower() for pub in 
                                ['wiley', 'pearson', "o'reilly", 'springer', 'press', 'publisher', 'edition', 'ed.'])
        if is_likely_book:
            # Find primary Google Books match (the first one returned by API)
            primary_google_books = next((c for c in scored_candidates if c.get('is_primary_google_books_match')), None)
            if primary_google_books and primary_google_books['match_score'] >= 35:
                # Use the primary (first) Google Books result - it's already sorted by relevance
                best_candidate = primary_google_books
                self.logger.info(f"Prioritizing PRIMARY Google Books result for book query (score: {best_candidate['match_score']})")
                self.logger.info(f"Selected book: {best_candidate.get('title', 'Unknown')} by {', '.join(best_candidate.get('authors', [])[:2])} ({best_candidate.get('year', 'N/A')})")
            else:
                # Fallback: use highest scoring Google Books result
                google_books_candidates = [c for c in scored_candidates if c.get('source') == 'google_books']
                if google_books_candidates and google_books_candidates[0]['match_score'] >= 40:
                    best_candidate = google_books_candidates[0]
                    self.logger.info(f"Prioritizing Google Books result for book query (score: {best_candidate['match_score']})")
                    self.logger.info(f"Selected book: {best_candidate.get('title', 'Unknown')} by {', '.join(best_candidate.get('authors', [])[:2])} ({best_candidate.get('year', 'N/A')})")
        
        # Otherwise, prefer candidates with DOI when scores are close
        if best_candidate.get('source') != 'google_books':
            doi_candidates = [c for c in scored_candidates if c.get('doi')]
            if doi_candidates:
                best_doi_candidate = doi_candidates[0]
                if (not best_candidate.get('doi') or
                    best_doi_candidate['match_score'] >= best_candidate['match_score'] - 5):
                    best_candidate = best_doi_candidate

        # If best does not have DOI but looks strong, try title-only CrossRef lookup to resolve DOI
        if (not best_candidate.get('doi')) and best_candidate.get('title') and best_candidate.get('match_score', 0) >= 85:
            try:
                resolved = self._resolve_doi_via_crossref_title(best_candidate['title'], query_string)
                if resolved and resolved.get('doi'):
                    best_candidate = resolved
            except Exception:
                pass
        
        # Decision logic
        if best_candidate['match_score'] >= 80:
            # High confidence: auto adopt
            if len(scored_candidates) == 1 or best_candidate['match_score'] - scored_candidates[1]['match_score'] > 10:
                self.logger.info(f"Entry {raw_entry['id']} high confidence match: {best_candidate.get('doi', 'no-doi')}")
                return {
                    'id': raw_entry['id'],
                    'raw_text': raw_entry['raw_text'],
                    'doi': best_candidate.get('doi'),
                    'arxiv_id': best_candidate.get('arxiv_id'),
                    'url': best_candidate.get('url'),
                    'metadata': best_candidate,
                    'status': 'identified'
                }
        
        if 70 <= best_candidate['match_score'] < 80:
            # Medium confidence: trigger interactive mode
            top_candidates = scored_candidates[:5]  # Top 5 candidates
            try:
                user_choice = interactive_callback(top_candidates)
                if 0 <= user_choice < len(top_candidates):
                    chosen_candidate = top_candidates[user_choice]
                    self.logger.info(f"Entry {raw_entry['id']} user selection: {chosen_candidate.get('doi', 'no-doi')}")
                    return {
                        'id': raw_entry['id'],
                        'raw_text': raw_entry['raw_text'],
                        'doi': chosen_candidate.get('doi'),
                        'arxiv_id': chosen_candidate.get('arxiv_id'),
                        'url': chosen_candidate.get('url'),
                        'metadata': chosen_candidate,
                        'status': 'identified'
                    }
                else:
                    # Non-interactive or user skipped: fallback to best candidate if sufficiently strong
                    if best_candidate['match_score'] >= 75:
                        self.logger.info(
                            f"Entry {raw_entry['id']} fallback adopt best candidate (score={best_candidate['match_score']}): {best_candidate.get('doi', 'no-doi')}"
                        )
                        return {
                            'id': raw_entry['id'],
                            'raw_text': raw_entry['raw_text'],
                            'doi': best_candidate.get('doi'),
                            'arxiv_id': best_candidate.get('arxiv_id'),
                            'url': best_candidate.get('url'),
                            'metadata': best_candidate,
                            'status': 'identified'
                        }
                    self.logger.info(f"Entry {raw_entry['id']} user skipped")
            except Exception as e:
                self.logger.error(f"Interactive callback failed: {str(e)}")
                # Fallback in case interactive path is unavailable
                if best_candidate['match_score'] >= 75:
                    self.logger.info(
                        f"Entry {raw_entry['id']} fallback adopt best candidate after interactive error (score={best_candidate['match_score']}): {best_candidate.get('doi', 'no-doi')}"
                    )
                    return {
                        'id': raw_entry['id'],
                        'raw_text': raw_entry['raw_text'],
                        'doi': best_candidate.get('doi'),
                        'arxiv_id': best_candidate.get('arxiv_id'),
                        'url': best_candidate.get('url'),
                        'metadata': best_candidate,
                        'status': 'identified'
                    }
        
        # Low confidence but if score is decent and has title, mark as identified
        # Lower threshold to avoid rejecting valid papers
        # For books, use even lower threshold (books often have less complete metadata)
        # Check if any keyword suggests this is a book
        is_best_candidate_book = (
            best_candidate.get('is_book') or 
            best_candidate.get('type') in ['book', 'monograph', 'edited-book', 'reference-book'] or
            any(publisher in best_candidate.get('publisher', '').lower() 
                for publisher in ['wiley', 'pearson', "o'reilly", 'springer'])
        )
        # For Google Books results, use even lower threshold (they're very accurate)
        if best_candidate.get('source') == 'google_books' and is_best_candidate_book:
            threshold = 35  # Very low threshold for Google Books + book detection
        elif is_best_candidate_book:
            threshold = 42  # Lower threshold for books
        else:
            threshold = 48  # Normal threshold for articles
        
        if best_candidate['match_score'] >= threshold and best_candidate.get('title'):
            self.logger.info(f"Entry {raw_entry['id']} adopting best candidate with score {best_candidate['match_score']} (type: {best_candidate.get('type', 'unknown')}, is_book: {is_best_candidate_book})")
            return {
                'id': raw_entry['id'],
                'raw_text': raw_entry['raw_text'],
                'doi': best_candidate.get('doi'),
                'arxiv_id': best_candidate.get('arxiv_id'),
                'url': best_candidate.get('url'),
                'metadata': best_candidate,
                'status': 'identified'
            }

        # Debug: Log the best candidate score for analysis
        self.logger.info(f"Entry {raw_entry['id']} best candidate score: {best_candidate.get('match_score', 0)}")
        if 'score_breakdown' in best_candidate:
            self.logger.info(f"Entry {raw_entry['id']} score breakdown: {best_candidate['score_breakdown']}")
        
        # Low confidence: mark as failed
        self.logger.warning(f"Entry {raw_entry['id']} low confidence match, marking as failed")
        return {
            'id': raw_entry['id'],
            'raw_text': raw_entry['raw_text'],
            'doi': None,
            'arxiv_id': None,
            'url': None,
            'metadata': {},
            'status': 'identification_failed'
        }

    def _resolve_doi_via_crossref_title(self, candidate_title: str, original_query: str) -> Optional[Dict]:
        """Try to resolve DOI by querying CrossRef with title only (plus hints). Returns a candidate dict with DOI if found and strongly matched."""
        try:
            url = f"{self.crossref_base_url}"
            # Build a focused query using title and optional year tokens from original query
            year_match = re.search(r"(19|20)\d{2}", original_query)
            year_text = year_match.group(0) if year_match else ''
            focused_query = candidate_title
            if year_text:
                focused_query = f"{candidate_title} {year_text}"
            params = {
                'query.title': candidate_title,
                'query.bibliographic': focused_query,
                'rows': 5,
                'mailto': 'onecite@users.noreply.github.com'
            }
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            items = data.get('message', {}).get('items', [])
            best_item = None
            best_score = -1
            for item in items:
                title = (item.get('title', [''])[0] or '').lower()
                if not title:
                    continue
                # Fuzzy comparison against candidate title
                base = candidate_title.lower()
                score = max(
                    fuzz.ratio(base, title),
                    fuzz.partial_ratio(base, title),
                    fuzz.token_set_ratio(base, title)
                )
                if score > best_score and item.get('DOI'):
                    best_score = score
                    best_item = item
            if best_item and best_score >= 90:
                return {
                    'source': 'crossref',
                    'doi': best_item.get('DOI'),
                    'title': (best_item.get('title', [''])[0] or ''),
                    'authors': [f"{a.get('given', '')} {a.get('family', '')}" for a in best_item.get('author', [])],
                    'year': _safe_year(best_item.get('published-print')) or _safe_year(best_item.get('published-online')),
                    'journal': best_item.get('container-title', [''])[0] if best_item.get('container-title') else '',
                    'citations': best_item.get('is-referenced-by-count', 0)
                }
        except Exception:
            return None
        return None
    
    def _search_crossref(self, query: str, limit: int = 15) -> List[Dict]:
        """CrossRef search with query optimization."""
        try:
            # Optimize query parameters
            params = {
                'query': query,
                'query.bibliographic': query,
                'query.title': query,
                'rows': limit,
                'sort': 'relevance',
                'mailto': 'onecite@users.noreply.github.com'
            }

            # Try multiple query strategies
            search_strategies = [
                params,  
                {**params, 'query.author': query.split('.')[0] if '.' in query else query},  
                {**params, 'filter': 'type:journal-article,proceedings-article,book-chapter,book,monograph'},  
            ]

            all_results = []
            seen_dois = set()

            for i, strategy_params in enumerate(search_strategies):
                try:
                    self.logger.debug(f"CrossRef search strategy {i+1}")
                    url = f"{self.crossref_base_url}"
                    response = requests.get(url, params=strategy_params, timeout=15)  
                    response.raise_for_status()
                    data = response.json()

                    for item in data.get('message', {}).get('items', []):
                        doi = item.get('DOI')
                        if not doi or doi in seen_dois:
                            continue

                        # More complete data extraction
                        result = {
                            'source': 'crossref',
                            'doi': doi,
                            'title': item.get('title', [''])[0] if item.get('title') else '',
                            'authors': [],
                            'year': None,
                            'journal': '',
                            'citations': item.get('is-referenced-by-count', 0),
                            'type': item.get('type', ''),
                            'url': f"https://doi.org/{doi}",
                            'publisher': item.get('publisher', ''),
                            'volume': item.get('volume', ''),
                            'issue': item.get('issue', ''),
                            'pages': item.get('page', ''),
                            'isbn': None,
                            'edition': item.get('edition-number', '')
                        }
                        
                        # Handle ISBN (book-specific)
                        if item.get('ISBN'):
                            isbns = item.get('ISBN', [])
                            if isbns:
                                result['isbn'] = isbns[0]  

                        # Process author information
                        for author in item.get('author', []):
                            if author.get('family') or author.get('given'):
                                author_name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                                if author_name:
                                    result['authors'].append(author_name)

                        # Handle publication year
                        published_dates = [
                            item.get('published-print', {}).get('date-parts'),
                            item.get('published-online', {}).get('date-parts'),
                            item.get('issued', {}).get('date-parts')
                        ]

                        for date_parts in published_dates:
                            if date_parts and date_parts[0] and date_parts[0][0]:
                                result['year'] = date_parts[0][0]
                                break

                        # Process journal/conference names
                        container_titles = item.get('container-title', [])
                        if container_titles:
                            result['journal'] = container_titles[0]

                        # Special treatment for conference papers
                        if result['type'] == 'proceedings-article':
                            event = item.get('event')
                            if event and event.get('name'):
                                result['journal'] = event['name'][0] if isinstance(event['name'], list) else event['name']
                        
                        # Special handling of books
                        if result['type'] in ['book', 'monograph', 'edited-book', 'reference-book']:
                            result['is_book'] = True
                            # Books usually do not have a journal, but have a publisher
                            if not result.get('publisher'):
                                result['publisher'] = item.get('publisher', '')

                        # Only keep results with enough information
                        # For books, author may be empty (edited books)
                        if result['title'] and len(result['title']) > 5:
                            if result.get('is_book') or result['authors']:
                                all_results.append(result)
                                seen_dois.add(doi)

                        if len(all_results) >= limit:
                            break

                    if len(all_results) >= limit:
                        break

                except requests.exceptions.Timeout:
                    self.logger.warning(f"CrossRef search strategy {i+1} timed out")
                    time.sleep(5)  
                    continue
                except Exception as e:
                    self.logger.warning(f"CrossRef search strategy {i+1} failed: {str(e)}")
                    time.sleep(2)  
                    continue

            self.logger.info(f"CrossRef search returned {len(all_results)} unique results")
            return all_results

        except Exception as e:
            self.logger.error(f"CrossRef search failed: {str(e)}")
            return []
    
    def _search_google_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Google Books API for book metadata"""
        try:
            # Strategy: Extract meaningful keywords - title and author last names
            query_clean = ""
            
            # Step 1: Find and extract title (after year, before edition/publisher)
            # Pattern: (YEAR). TITLE (edition). Publisher
            title_pattern = r'\(\d{4}\)\.\s*([^.(]+?)(?:\s*\([^)]*ed\.\)|\.)'
            title_match = re.search(title_pattern, query)
            
            if title_match:
                title_text = title_match.group(1).strip()
                # Remove italic markers
                title_text = re.sub(r'\*([^*]+)\*', r'\1', title_text)
                query_clean = title_text
            else:
                # Fallback: try to find text between periods
                parts = query.split('.')
                for part in parts:
                    part = part.strip()
                    # Skip author parts and years
                    if len(part) > 20 and not re.match(r'^[A-Z][a-z]+,', part) and not re.search(r'^\d{4}$', part):
                        query_clean = re.sub(r'\*([^*]+)\*', r'\1', part)
                        break
            
            # Step 2: Extract author last names
            # Pattern: Name, Initial.
            author_parts = re.findall(r'([A-Z][a-z]+),\s*[A-Z]\.', query)
            if author_parts:
                query_clean += ' ' + ' '.join(author_parts[:2])  # Use up to 2 authors
            
            # If query_clean is still empty, use original
            if not query_clean or len(query_clean) < 5:
                query_clean = query.strip()
            
            self.logger.info(f"Google Books query: {query_clean}")
            
            base_url = "https://www.googleapis.com/books/v1/volumes"
            params = {
                'q': query_clean,
                'maxResults': limit,
                'printType': 'books',
                'langRestrict': 'en'
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            results = []
            for item in items:
                volume_info = item.get('volumeInfo', {})
                
                result = {
                    'source': 'google_books',
                    'is_book': True,
                    'type': 'book',
                    'title': volume_info.get('title', ''),
                    'authors': volume_info.get('authors', []),
                    'publisher': volume_info.get('publisher', ''),
                    'year': None,
                    'isbn': None,
                    'pages': volume_info.get('pageCount', ''),
                    'url': volume_info.get('infoLink', ''),
                    'citations': 0  # Google Books doesn't provide citation counts
                }
                
                # Extract year from publishedDate (format: YYYY-MM-DD or YYYY)
                published_date = volume_info.get('publishedDate', '')
                if published_date:
                    year_match = re.search(r'\b(19|20)\d{2}\b', published_date)
                    if year_match:
                        result['year'] = int(year_match.group())
                
                industry_identifiers = volume_info.get('industryIdentifiers', [])
                for identifier in industry_identifiers:
                    if identifier.get('type') in ['ISBN_13', 'ISBN_10']:
                        result['isbn'] = identifier.get('identifier')
                        break
                
                # Extract edition if mentioned in title or subtitle
                subtitle = volume_info.get('subtitle', '')
                full_title = f"{result['title']} {subtitle}".lower()
                edition_match = re.search(r'(\d+)(?:st|nd|rd|th)?\s+(?:ed\.|edition)', full_title)
                if edition_match:
                    result['edition'] = edition_match.group(1)
                
                # Only add if has title and authors
                if result['title'] and result['authors']:
                    results.append(result)
            
            self.logger.info(f"Google Books search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.warning(f"Google Books search failed: {str(e)}")
            return []
    
    def _search_google_scholar(self, query: str, limit: int = 5) -> List[Dict]:
        """Search in Google Scholar (with retry and captcha handling)."""
        try:
            import threading
            import time

            # Add delay between requests to avoid rate limiting
            if hasattr(self, '_last_scholar_request'):
                time_since_last = time.time() - self._last_scholar_request
                if time_since_last < 10.0:  
                    time.sleep(10.0 - time_since_last)

            self._last_scholar_request = time.time()

            # Retry with fewer attempts and longer delay
            max_retries = 2  
            for attempt in range(max_retries):
                if attempt > 0:
                    # Large incremental delays: 30 seconds, 60 seconds
                    retry_delay = 30 * (attempt + 1)
                    self.logger.info(f"Google Scholar retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay")
                    time.sleep(retry_delay)

                results = []
                search_completed = [False]
                error_occurred = [None]
                captcha_solved = [False]

                def search_worker():
                    try:
                        self.logger.info(f"Google Scholar search attempt {attempt + 1}: {query[:50]}...")
                        search_query = scholarly.search_pubs(query)

                        count = 0
                        for pub in search_query:
                            if count >= limit:
                                break

                            # Dynamic timeout check
                            elapsed = time.time() - self._last_scholar_request
                            if elapsed > 20:  
                                self.logger.warning("Google Scholar search taking too long, stopping")
                                break

                            try:
                                bib = pub.get('bib', {})

                                result = {
                                    'source': 'google_scholar',
                                    'doi': None,
                                    'title': bib.get('title', '') or pub.get('title', ''),
                                    'authors': bib.get('author', []) if isinstance(bib.get('author'), list) else
                                              (bib.get('author').split(' and ') if bib.get('author') else []),
                                    'year': bib.get('pub_year', '') or pub.get('year'),
                                    'journal': bib.get('venue', '') or pub.get('venue', '') or pub.get('journal', ''),
                                    'citations': pub.get('num_citations', 0),
                                    'url': pub.get('pub_url', '') or pub.get('url', ''),
                                    'arxiv_id': None
                                }

                                # Try to extract arXiv ID from eprint or other fields
                                if 'eprint' in pub:
                                    arxiv_match = re.search(r'(\d{4}\.\d{4,5})', pub['eprint'])
                                    if arxiv_match:
                                        result['arxiv_id'] = arxiv_match.group(1)

                                if result['url'] and 'doi.org' in result['url']:
                                    doi_match = re.search(r'doi\.org/(.+)', result['url'])
                                    if doi_match:
                                        result['doi'] = doi_match.group(1)

                                # For conference papers, venue often contains conference name
                                if result['journal'] and ('conference' in result['journal'].lower() or
                                                         'proceedings' in result['journal'].lower() or
                                                         'nips' in result['journal'].lower() or
                                                         'neurips' in result['journal'].lower()):
                                    result['type'] = 'conference'

                                # Filter out empty or incomplete results
                                if result['title'] and len(result['title']) > 5:
                                    results.append(result)
                                    count += 1

                            except Exception as e:
                                self.logger.warning(f"Error processing Google Scholar result: {str(e)}")
                                continue

                        search_completed[0] = True
                        self.logger.info(f"Google Scholar search completed, found {len(results)} valid results")

                    except Exception as e:
                        error_msg = str(e)
                        error_occurred[0] = error_msg
                        search_completed[0] = True

                        # Detect verification codes and throttling errors
                        is_captcha_error = any(keyword in error_msg.lower() for keyword in [
                            'captcha', 'blocked', 'rate', 'too many', '429', 'forbidden', 'access denied'
                        ])

                        if is_captcha_error:
                            self.logger.warning(f"Google Scholar captcha/rate limit detected: {error_msg}")
                        else:
                            self.logger.warning(f"Google Scholar search error: {error_msg}")

                # Start search thread
                search_thread = threading.Thread(target=search_worker)
                search_thread.daemon = True
                search_thread.start()

                # Wait for search to complete, dynamically adjust wait time - significantly increase timeout
                max_wait_iterations = 120
                for i in range(max_wait_iterations):
                    if search_completed[0]:
                        break
                    time.sleep(0.5)

                # Check search results
                if search_completed[0]:
                    if error_occurred[0]:
                        error_msg = error_occurred[0]
                        is_captcha_error = any(keyword in error_msg.lower() for keyword in [
                            'captcha', 'blocked', 'rate', 'too many', '429', 'forbidden', 'access denied'
                        ])

                        if is_captcha_error and attempt < max_retries - 1:
                            # The verification code is wrong and there is still a chance to retry. Please wait longer for the verification code system to cool down.
                            self.logger.info("Captcha error detected, will retry with extended backoff...")
                            time.sleep(60)  
                            continue
                        else:
                            # Other errors or the maximum number of retries has been reached
                            self.logger.warning(f"Google Scholar search failed after retries: {error_msg}")
                            return []
                    else:
                        # Successfully obtained results
                        self.logger.info(f"Google Scholar search succeeded with {len(results)} results")
                        return results

                else:
                    # Search timeout - possible captcha issue, adding extra delay
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Google Scholar search timed out, likely due to captcha. Adding cooling period...")
                        time.sleep(120)  
                        continue
                    else:
                        self.logger.warning(f"Google Scholar search failed after {max_retries} attempts (timeout)")
                        return []

            return []

        except Exception as e:
            self.logger.warning(f"Google Scholar search failed: {str(e)}")
            return []
    
    def _score_candidates(self, candidates: List[Dict], query_string: str) -> List[Dict]:
        """Score candidates with domain-specific adjustments."""
        scored_candidates = []

        # Normalize query for title matching
        normalized_query = query_string.strip()
        # Try to derive a probable title part: cut at first 4-digit year
        title_part = re.split(r'\b(19|20)\d{2}\b', normalized_query)[0].strip() or normalized_query
        # Remove common "et al." noise
        title_part = re.sub(r'\bet\s*al\.?\b', '', title_part, flags=re.IGNORECASE).strip()

        # Domain-specific venue synonyms
        synonyms = {
            'nips': 'neural information processing systems',
            'neurips': 'neural information processing systems',
            'cvpr': 'computer vision and pattern recognition',
            'iclr': 'international conference on learning representations',
            'icml': 'international conference on machine learning',
            # Health information systems domain
            'dhis2': 'district health information system 2',
            'dhis': 'district health information system',
            'who': 'world health organization',
            'bmj': 'british medical journal',
            'plos': 'public library of science',
            'bmc': 'biomed central'
        }

        normalized_query_lower = normalized_query.lower()
        for k, v in synonyms.items():
            if k in normalized_query_lower and v not in normalized_query_lower:
                normalized_query += f" {v}"

        # Also normalize candidate journal/venue names
        def normalize_venue(venue):
            if not venue:
                return ""
            venue_lower = venue.lower()
            for k, v in synonyms.items():
                if k in venue_lower:
                    return venue.replace(k, v).replace(k.upper(), v)
            return venue

        query_year = None
        year_match = re.search(r'\b(19|20)\d{2}\b', normalized_query)
        if year_match:
            query_year = int(year_match.group(0))

        for candidate in candidates:
            scores = {}

            # Title similarity
            candidate_title = candidate.get('title', '').lower()
            base_title = title_part.lower()

            if candidate_title and base_title:
                # Use multiple fuzzy measures and take the best
                ratio = fuzz.ratio(base_title, candidate_title)
                partial = fuzz.partial_ratio(base_title, candidate_title)
                token_sort = fuzz.token_sort_ratio(base_title, candidate_title)
                token_set = fuzz.token_set_ratio(base_title, candidate_title)

                title_score = max(ratio, partial, token_sort, token_set)

                # Bonus for exact phrase matches
                if base_title in candidate_title or candidate_title in base_title:
                    title_score = min(title_score + 20, 100)

                scores['title'] = title_score
            else:
                scores['title'] = 0

            # Author matching (improved)
            author_score = 0
            if candidate.get('authors'):
                authors_text = ' '.join(candidate['authors']).lower()
                query_lower = normalized_query.lower()

                # Exact author name matching
                exact_author_match = False
                for author in candidate['authors']:
                    author_clean = author.lower().strip()
                    if author_clean in query_lower:
                        exact_author_match = True
                        break

                if exact_author_match:
                    author_score = 80
                else:
                    # Fuzzy author matching
                    author_score = fuzz.partial_ratio(query_lower, authors_text)

                # Bonus for multiple authors
                if len(candidate['authors']) > 1:
                    author_score = min(author_score + 10, 100)

            scores['author'] = author_score

            # Year matching (critical for academic papers)
            year_score = 0
            if candidate.get('year') and query_year:
                try:
                    candidate_year = int(candidate['year'])
                except (ValueError, TypeError):
                    candidate_year = None
                if candidate_year:
                    year_diff = abs(candidate_year - query_year)
                    if year_diff == 0:
                        year_score = 100  # Perfect year match
                    elif year_diff <= 2:
                        year_score = 70  # Close year match
                    elif year_diff <= 5:
                        year_score = 30  # Reasonable year match

            scores['year'] = year_score

            # Venue/Journal matching
            venue_score = 0
            venue_lower = ""  # Initialize venue_lower
            if candidate.get('journal'):
                normalized_venue = normalize_venue(candidate['journal'])
                venue_lower = normalized_venue.lower()

                # Check for venue mentions in query
                if venue_lower and venue_lower in normalized_query_lower:
                    venue_score = 60
                else:
                    # Fuzzy venue matching
                    venue_ratio = fuzz.partial_ratio(normalized_query_lower, venue_lower)
                    if venue_ratio > 60:
                        venue_score = venue_ratio * 0.8

            scores['venue'] = venue_score

            # Source reliability score
            source_score = 0
            if candidate.get('source') == 'crossref':
                source_score = 90  # CrossRef is highly reliable
            elif candidate.get('source') == 'pubmed':
                source_score = 98  # PubMed is most reliable for medical literature
            elif candidate.get('source') == 'semantic_scholar':
                source_score = 92  # Semantic Scholar is very good, automation-driven
            elif candidate.get('source') == 'google_books':
                source_score = 95  # Google Books is very reliable for books
            elif candidate.get('source') == 'datacite':
                source_score = 88  # DataCite is reliable for datasets
            elif candidate.get('source') == 'google_scholar':
                source_score = 70  # Google Scholar is good but less structured
            elif candidate.get('source') == 'zenodo':
                source_score = 85  # Zenodo is reliable

            scores['source'] = source_score

            # Citation score (adjusted for field and age)
            citation_score = 0
            if candidate.get('citations') is not None:
                citations = candidate['citations']
                if citations > 1000:
                    citation_score = 100
                elif citations > 100:
                    citation_score = 80
                elif citations > 10:
                    citation_score = 50
                elif citations > 0:
                    citation_score = 20
                # Books often have fewer citations, give them base score
                elif candidate.get('is_book') or candidate.get('type') in ['book', 'monograph']:
                    citation_score = 30

            scores['citations'] = citation_score

            # DOI presence score - CRITICAL
            doi_score = 0
            if candidate.get('doi'):
                doi_score = 100
            scores['doi'] = doi_score

            # Domain-specific bonuses
            domain_bonus = 0
            authors_text = ' '.join(candidate['authors']).lower() if candidate.get('authors') else ''
            candidate_text = f"{candidate_title} {authors_text} {venue_lower}".lower()
            
            # Book bonus
            if candidate.get('is_book') or candidate.get('type') in ['book', 'monograph']:
                domain_bonus += 20  # Books deserve bonus (increased from 15)
                
                # Google Books source bonus - they're very accurate for books
                if candidate.get('source') == 'google_books':
                    domain_bonus += 30  # Extra bonus for Google Books results (increased from 20)
                
                # Well-known publishers bonus
                publisher = candidate.get('publisher', '').lower()
                known_publishers = ['wiley', 'pearson', 'springer', 'elsevier', "o'reilly", 
                                   'cambridge university press', 'oxford university press', 
                                   'mit press', 'academic press', 'morgan kaufmann', 'addison wesley']
                if any(pub in publisher for pub in known_publishers):
                    domain_bonus += 20  # Increased from 15

            # Health information systems keywords
            health_keywords = ['health information', 'dhis', 'district health', 'routine health',
                             'health system', 'health data', 'public health', 'epidemiology']

            if any(keyword in candidate_text for keyword in health_keywords):
                domain_bonus += 15

            # WHO/International organization bonus
            if 'world health organization' in candidate_text or 'who' in candidate_text:
                domain_bonus += 20

            # BMC/PLOS bonus (open access, high quality)
            if any(pub in venue_lower for pub in ['bmc', 'plos', 'biomed central', 'public library of science']):
                domain_bonus += 10

            scores['domain'] = domain_bonus

            # Weighted total score calculation (adjusted for version tolerance)
            # For books, year is even less important (many editions/reprints)
            is_candidate_book = candidate.get('is_book') or candidate.get('type') in ['book', 'monograph']
            
            if is_candidate_book:
                # Book-specific weights: year matters less, title and publisher matter more
                match_score = (
                    scores['title'] * 0.40 +      # Title most important for books
                    scores['author'] * 0.25 +     # Author very important
                    scores['year'] * 0.02 +       # Year much less critical for books
                    scores['venue'] * 0.05 +      # Venue less relevant for books
                    scores['source'] * 0.08 +     # Source reliability more important
                    scores['citations'] * 0.02 +  # Citations least important
                    scores['domain'] * 0.08 +     # Domain/publisher bonus
                    scores['doi'] * 0.10          # DOI bonus
                )
            else:
                # Article weights - DOI is heavily weighted
                match_score = (
                    scores['title'] * 0.30 +      # Title important
                    scores['author'] * 0.25 +     # Author important
                    scores['year'] * 0.08 +       # Year less critical
                    scores['venue'] * 0.07 +      # Venue helpful
                    scores['source'] * 0.05 +     # Source reliability
                    scores['citations'] * 0.03 +  # Citations least important
                    scores['domain'] * 0.02 +     # Domain bonus
                    scores['doi'] * 0.20          # DOI is extremely important (20% weight)
                )

            match_score = min(max(match_score, 0), 100)
            candidate_copy = candidate.copy()
            candidate_copy['match_score'] = round(match_score, 2)
            candidate_copy['score_breakdown'] = scores
            scored_candidates.append(candidate_copy)

        # Sort by match score descending
        scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)

        return scored_candidates


class EnricherModule:
    """Stage 3: Enrichment and Validation Module."""
    
    def __init__(self, use_google_scholar: bool = False):
        """Initialize the enricher module.

        Args:
            use_google_scholar: Enable Google Scholar lookups when
                ``True``.  Defaults to ``False``.
        """
        self.logger = logging.getLogger(__name__)
        self.crossref_base_url = "https://api.crossref.org/works"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.use_google_scholar = use_google_scholar
        self._used_keys: set = set()
        self._crossref_headers = {
            'Accept': 'application/json',
            'User-Agent': f'OneCite/0.1.0 (https://github.com/HzaCode/OneCite; mailto:onecite@users.noreply.github.com)',
        }
        self._crossref_mailto = 'onecite@users.noreply.github.com'
    
    def enrich(self, identified_entries: List[IdentifiedEntry], 
               template: Dict, raw_entries: List[RawEntry] = None) -> List[CompletedEntry]:
        """Enrich entries to obtain complete bibliographic information.

        Args:
            identified_entries: List of identified entries from
                :meth:`IdentifierModule.identify`.
            template: Template configuration dictionary that controls
                which fields to collect.
            raw_entries: Optional list of raw entries used to preserve
                original BibTeX fields.

        Returns:
            A list of :class:`CompletedEntry` dictionaries.
        """
        self.logger.info(f"Starting enrichment for {len(identified_entries)} entries")
        completed_entries = []
        
        # Create a mapping from entry id to raw_entry for quick lookup
        raw_entries_map = {}
        if raw_entries:
            raw_entries_map = {entry['id']: entry for entry in raw_entries}
            self.logger.debug(f"Created raw_entries_map with {len(raw_entries_map)} entries")
        else:
            self.logger.warning("raw_entries is None or empty - original fields will not be preserved!")
        
        for entry in identified_entries:
            if entry['status'] == 'identified':
                # Process entries with DOI, arXiv ID, or other metadata
                if entry.get('doi') or entry.get('arxiv_id') or entry.get('metadata'):
                    # Get corresponding raw_entry
                    raw_entry = raw_entries_map.get(entry['id'])
                    if not raw_entry:
                        self.logger.warning(f"Entry {entry['id']}: No raw_entry found in map!")
                    completed_entry = self._enrich_single_entry(entry, template, raw_entry)
                    completed_entries.append(completed_entry)
                else:
                    # Entries without any identifier
                    failed_entry = {
                        'id': entry['id'],
                        'doi': '',
                        'status': 'enrichment_failed',
                        'bib_key': '',
                        'bib_data': {}
                    }
                    completed_entries.append(failed_entry)
            else:
                # Entries that were not identified are marked as failed
                failed_entry = {
                    'id': entry['id'],
                    'doi': '',
                    'status': 'enrichment_failed',
                    'bib_key': '',
                    'bib_data': {}
                }
                completed_entries.append(failed_entry)
        
        successful_count = sum(1 for e in completed_entries if e['status'] == 'completed')
        self.logger.info(f"Enrichment completed: {successful_count}/{len(completed_entries)} entries successfully completed")
        
        return completed_entries
    
    def _enrich_single_entry(self, identified_entry: IdentifiedEntry, 
                            template: Dict, raw_entry: RawEntry = None) -> CompletedEntry:
        """Enrich a single entry"""
        doi = identified_entry.get('doi')
        arxiv_id = identified_entry.get('arxiv_id')
        metadata = identified_entry.get('metadata', {})
        
        try:
            base_record = None
            
            # Check if it's GitHub software or Zenodo dataset
            if metadata.get('source') in ['github', 'zenodo', 'figshare']:
                # Use metadata directly (already complete from API)
                base_record = self._convert_search_metadata(metadata)
            # Try to get metadata from various sources
            elif doi:
                # Get base record fromCrossref
                base_record = self._get_crossref_metadata(doi)
            elif arxiv_id:
                # Get base record from arXiv
                base_record = self._get_arxiv_metadata(arxiv_id)
            elif metadata:
                # Use metadata from search results
                base_record = self._convert_search_metadata(metadata)
            
            if not base_record:
                return {
                    'id': identified_entry['id'],
                    'doi': doi or '',
                    'status': 'enrichment_failed',
                    'bib_key': '',
                    'bib_data': {}
                }
            
            # Generate BibTeX key
            bib_key = self._generate_bibtex_key(base_record)
            
            # Fill in missing fields per template
            completed_data = self._complete_fields(base_record, template)
            
            # Preserve original BibTeX entry fields when available
            if raw_entry and raw_entry.get('original_entry'):
                original = raw_entry['original_entry']
                self.logger.info(f"Entry {identified_entry['id']}: Found original_entry with keys: {list(original.keys()) if original else 'None'}")
                
                preserve_fields = ['author', 'year', 'title', 'journal', 'publisher', 
                                   'volume', 'number', 'pages', 'note', 'howpublished', 
                                   'address', 'edition', 'month']
                
                for field in preserve_fields:
                    if field in original and original[field]:
                        # Check if API data differs significantly
                        api_value = completed_data.get(field)
                        original_value = original[field]
                        
                        # Preserve original if it exists and is not empty
                        if original_value and str(original_value).strip():
                            # Log when we're overriding API data
                            if api_value and api_value != original_value:
                                self.logger.info(f"Entry {identified_entry['id']}: Preserving original {field}='{original_value}' instead of API value '{api_value}'")
                            completed_data[field] = original_value
            else:
                self.logger.warning(f"Entry {identified_entry['id']}: No original_entry available in raw_entry - raw_entry={raw_entry is not None}")
            
            # Set the entry type based on content
            is_thesis_type = (
                metadata.get('is_thesis') == True or
                metadata.get('type') in ['phdthesis', 'mastersthesis', 'thesis'] or
                base_record.get('is_thesis') == True
            )
            
            is_software_type = (
                metadata.get('is_software') == True or
                metadata.get('type') == 'software' or
                base_record.get('is_software') == True
            )
            
            is_dataset_type = (
                metadata.get('is_dataset') == True or
                metadata.get('type') == 'dataset' or
                base_record.get('is_dataset') == True
            )
            
            is_book_type = (
                metadata.get('is_book') == True or 
                str(metadata.get('is_book')).lower() == 'true' or
                metadata.get('type') in ['book', 'monograph', 'edited-book', 'reference-book'] or
                base_record.get('is_book') == True or
                str(base_record.get('is_book')).lower() == 'true'
            )
            
            if is_thesis_type:
                # Use thesis_type from metadata if available
                thesis_type = metadata.get('thesis_type', 'phdthesis')
                completed_data['ENTRYTYPE'] = thesis_type
            elif is_software_type:
                completed_data['ENTRYTYPE'] = 'software'
            elif is_dataset_type:
                completed_data['ENTRYTYPE'] = 'misc'
                # Add how published for datasets
                if not completed_data.get('howpublished'):
                    publisher = completed_data.get('publisher', 'Online')
                    completed_data['howpublished'] = f"\\url{{{completed_data.get('url', '')}}}"
            elif is_book_type:
                completed_data['ENTRYTYPE'] = 'book'
            elif metadata.get('type') == 'conference' or 'conference' in completed_data.get('journal', '').lower():
                completed_data['ENTRYTYPE'] = 'inproceedings'
            else:
                completed_data['ENTRYTYPE'] = template.get('entry_type', '@article').lstrip('@')
            
            completed_data['ID'] = bib_key
            
            # Add DOI if available
            if doi:
                completed_data['doi'] = doi
            
            # Add arXiv ID if available
            if arxiv_id:
                completed_data['arxiv'] = arxiv_id
                if not completed_data.get('url'):
                    completed_data['url'] = f'https://arxiv.org/abs/{arxiv_id}'
            
            self.logger.info(f"Entry {identified_entry['id']} enrichment successful")
            
            return {
                'id': identified_entry['id'],
                'doi': doi or '',
                'status': 'completed',
                'bib_key': bib_key,
                'bib_data': completed_data
            }
            
        except Exception as e:
            self.logger.error(f"Entry {identified_entry['id']} enrichment failed: {str(e)}")
            return {
                'id': identified_entry['id'],
                'doi': doi or '',
                'status': 'enrichment_failed',
                'bib_key': '',
                'bib_data': {}
            }
    
    def _strip_html_tags(self, text: str) -> str:
        """Strip HTML/XML tags from text and convert to plain text."""
        if not text:
            return text
        
        # Remove all HTML/XML tags first (replace with space to avoid word concatenation)
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        
        # Unescape HTML entities (may need multiple passes for double-escaped entities)
        clean_text = unescape(unescape(clean_text))
        
        # Clean up extra spaces that may result
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def _get_crossref_metadata(self, doi: str) -> Optional[Dict]:
        """Get metadata from the Crossref API"""
        try:
            url = f"{self.crossref_base_url}/{doi}"
            params = {'mailto': self._crossref_mailto}
            response = requests.get(url, headers=self._crossref_headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            work = data.get('message', {})
            
            # Extract title and clean HTML tags
            raw_title = work.get('title', [''])[0] if work.get('title') else ''
            clean_title = self._strip_html_tags(raw_title)
            
            # Convert to a standard format
            metadata = {
                'doi': work.get('DOI'),
                'title': clean_title,
                'author': self._format_authors(work.get('author', [])),
                'journal': work.get('container-title', [''])[0] if work.get('container-title') else '',
                'year': self._extract_year(work),
                'volume': work.get('volume'),
                'number': work.get('issue'),
                'pages': work.get('page'),
                'publisher': work.get('publisher'),
                'url': work.get('URL'),
                'type': work.get('type', ''),
                'abstract': work.get('abstract')  # Extract abstract if available
            }
            
            # Clean up abstract HTML tags if present
            if metadata['abstract']:
                metadata['abstract'] = self._strip_html_tags(metadata['abstract'])
            
            # Book specific fields
            if work.get('type') in ['book', 'monograph', 'edited-book', 'reference-book']:
                metadata['is_book'] = True
                # ISBN
                if work.get('ISBN'):
                    isbns = work.get('ISBN', [])
                    if isbns:
                        metadata['isbn'] = isbns[0]
                # Edition
                if work.get('edition-number'):
                    metadata['edition'] = str(work.get('edition-number'))
                # Address/location information for books
                if work.get('publisher-location'):
                    metadata['address'] = work.get('publisher-location')
            
            return {k: v for k, v in metadata.items() if v is not None}
            
        except Exception as e:
            self.logger.error(f"Failed to get CrossRef metadata for {doi}: {str(e)}")
            return None
    
    def _get_arxiv_metadata(self, arxiv_id: str) -> Optional[Dict]:
        """Get metadata from arXiv API (with timeout protection)"""
        try:
            import feedparser
            import requests
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            
            # Use requests to get content with timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            if not feed.entries:
                return None
            
            entry = feed.entries[0]
            
            authors = []
            for author in entry.get('authors', []):
                name = author.get('name', '')
                if name:
                    # Convert "First Last" to "Last, First"
                    parts = name.split()
                    if len(parts) >= 2:
                        authors.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
                    else:
                        authors.append(name)
            
            # Extract year from published date
            published = entry.get('published', '')
            year = published[:4] if len(published) >= 4 else None
            
            metadata = {
                'arxiv': arxiv_id,
                'title': entry.get('title', '').replace('\n', ' ').strip(),
                'author': ' and '.join(authors),
                'year': year,
                'url': f'https://arxiv.org/abs/{arxiv_id}',
                'abstract': entry.get('summary', '').replace('\n', ' ').strip()
            }
            
            return {k: v for k, v in metadata.items() if v}
            
        except Exception as e:
            self.logger.error(f"Failed to get arXiv metadata for {arxiv_id}: {str(e)}")
            return None
    
    def _convert_search_metadata(self, metadata: Dict) -> Optional[Dict]:
        """Convert search result metadata to standard format"""
        try:
            # Handle authors - they might be in list or string format
            authors = metadata.get('authors', []) or metadata.get('author', '')
            if isinstance(authors, list):
                formatted_authors = ' and '.join(authors)
            elif isinstance(authors, str) and authors.strip():
                formatted_authors = authors.strip()
            else:
                formatted_authors = ''
            
            # Determine type: thesis, software, dataset, book, conference, or journal article
            journal = metadata.get('journal', '')
            is_thesis = metadata.get('is_thesis') or metadata.get('type') in ['phdthesis', 'mastersthesis', 'thesis']
            is_software = metadata.get('is_software') or metadata.get('type') == 'software'
            is_dataset = metadata.get('is_dataset') or metadata.get('type') == 'dataset'
            is_book = metadata.get('is_book') or metadata.get('type') in ['book', 'monograph', 'edited-book', 'reference-book']
            is_conference = (
                metadata.get('type') in ('conference', 'proceedings-article')
                or metadata.get('booktitle')
                or any(conf in journal.lower()
                       for conf in ['conference', 'proceedings', 'symposium', 'workshop', 'nips', 'neurips'])
            )
            
            if is_thesis:
                # For thesis/dissertations
                result = {
                    'title': metadata.get('title', ''),
                    'author': formatted_authors,
                    'school': metadata.get('school', ''),
                    'year': str(metadata.get('year', '')),
                }
                if metadata.get('url'):
                    result['url'] = metadata['url']
                if metadata.get('thesis_type'):
                    result['type'] = metadata['thesis_type']
            elif is_software:
                # For software packages
                result = {
                    'title': metadata.get('title', ''),
                    'author': formatted_authors,
                    'publisher': metadata.get('publisher', 'GitHub'),
                    'year': str(metadata.get('year', '')),
                }
                if metadata.get('version'):
                    result['version'] = metadata['version']
                if metadata.get('url'):
                    result['url'] = metadata['url']
            elif is_dataset:
                # For datasets
                result = {
                    'title': metadata.get('title', ''),
                    'author': formatted_authors,
                    'year': str(metadata.get('year', '')),
                    'howpublished': metadata.get('publisher', 'Online')
                }
                if metadata.get('url'):
                    result['url'] = metadata['url']
                if metadata.get('version'):
                    result['version'] = metadata['version']
            elif is_book:
                # For books
                result = {
                    'title': metadata.get('title', ''),
                    'author': formatted_authors,
                    'publisher': metadata.get('publisher', ''),
                    'year': str(metadata.get('year', '')),
                }
                # Add book-specific fields
                if metadata.get('edition'):
                    result['edition'] = str(metadata['edition'])
                if metadata.get('isbn'):
                    result['isbn'] = metadata['isbn']
                if metadata.get('address'):
                    result['address'] = metadata['address']
            elif is_conference:
                # For conference papers, use booktitle instead of journal
                result = {
                    'title': metadata.get('title', ''),
                    'author': formatted_authors,
                    'booktitle': journal,
                    'year': str(metadata.get('year', '')),
                }
            else:
                # For journal articles
                result = {
                    'title': metadata.get('title', ''),
                    'author': formatted_authors,
                    'journal': journal,
                    'year': str(metadata.get('year', '')),
                }
            
            # Add optional fields (common to all types)
            if metadata.get('doi'):
                result['doi'] = metadata['doi']
            if metadata.get('url'):
                result['url'] = metadata['url']
            if metadata.get('arxiv_id'):
                result['arxiv'] = metadata['arxiv_id']
            if metadata.get('pages'):
                result['pages'] = metadata['pages']
            if not is_book:
                if metadata.get('volume'):
                    result['volume'] = metadata['volume']
                number = metadata.get('number') or metadata.get('issue')
                if number:
                    result['number'] = number
            
            return {k: v for k, v in result.items() if v}
            
        except Exception as e:
            self.logger.error(f"Failed to convert search metadata: {str(e)}")
            return None
    
    def _format_authors(self, authors: List[Dict]) -> str:
        """Format the author list"""
        formatted_authors = []
        for author in authors:
            if author.get('name'):
                formatted_authors.append(author['name'])
            else:
                given = author.get('given', '')
                family = author.get('family', '')
                if family and given:
                    formatted_authors.append(f"{family}, {given}")
                elif family:
                    formatted_authors.append(family)
                elif given:
                    formatted_authors.append(given)
        
        return ' and '.join(formatted_authors)
    
    def _extract_year(self, work: Dict) -> Optional[str]:
        """Extract publication year"""
        # Try multiple date fields
        date_fields = ['published-print', 'published-online', 'created']
        for field in date_fields:
            if field in work:
                date_parts = work[field].get('date-parts', [[]])
                if date_parts and date_parts[0]:
                    return str(date_parts[0][0])
        return None
    
    def _generate_bibtex_key(self, metadata: Dict) -> str:
        """Generate BibTeX key"""
        # Format: First author's surname + year + first word of the title
        key_parts = []
        
        # First author's surname
        if metadata.get('author'):
            first_author = metadata['author'].split(' and ')[0]
            if ',' in first_author:
                family_name = first_author.split(',')[0].strip()
            else:
                family_name = first_author.split()[-1]
            key_parts.append(re.sub(r'[^\w]', '', family_name))
        
        # Year
        if metadata.get('year'):
            key_parts.append(metadata['year'])
        
        # First word of title
        if metadata.get('title'):
            title_words = metadata['title'].split()
            if title_words:
                first_word = re.sub(r'[^\w]', '', title_words[0])
                key_parts.append(first_word)
        
        base_key = ''.join(key_parts) or 'unknown'
        key = base_key
        suffix = ord('a')
        while key in self._used_keys:
            key = f"{base_key}{chr(suffix)}"
            suffix += 1
        self._used_keys.add(key)
        return key
    
    def _complete_fields(self, base_record: Dict, template: Dict) -> Dict:
        """Return base_record unchanged; field completion via external sources removed."""
        return base_record.copy()
    
    def _get_pubmed_abstract(self, base_record: Dict) -> Optional[str]:
        """Get abstract from PubMed using DOI or title/author search."""
        try:
            doi = base_record.get('doi')
            pmid = None
            
            # Step 1: Try to find PMID by DOI
            if doi:
                url = f"{self.pubmed_base}/esearch.fcgi"
                params = {
                    'db': 'pubmed',
                    'term': f'{doi}[DOI]',
                    'retmode': 'json',
                    'retmax': 1
                }
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                idlist = data.get('esearchresult', {}).get('idlist', [])
                if idlist:
                    pmid = idlist[0]
                    self.logger.info(f"Found PMID {pmid} for DOI {doi}")
            
            # Step 2: If no PMID found by DOI, try searching by title
            if not pmid:
                title = base_record.get('title', '')
                if title:
                    # Clean title for search
                    search_title = re.sub(r'[^\w\s]', ' ', title).strip()
                    url = f"{self.pubmed_base}/esearch.fcgi"
                    params = {
                        'db': 'pubmed',
                        'term': search_title,
                        'retmode': 'json',
                        'retmax': 3
                    }
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    idlist = data.get('esearchresult', {}).get('idlist', [])
                    if idlist:
                        pmid = idlist[0]
                        self.logger.info(f"Found PMID {pmid} by title search")
            
            # Step 3: Fetch abstract by PMID
            if pmid:
                url = f"{self.pubmed_base}/efetch.fcgi"
                params = {
                    'db': 'pubmed',
                    'id': pmid,
                    'retmode': 'xml'
                }
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                # Parse XML to get abstract
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                # Handle structured abstracts (multiple AbstractText with Label)
                abstract_elems = root.findall('.//Abstract/AbstractText')
                if abstract_elems:
                    parts = []
                    for elem in abstract_elems:
                        label = elem.get('Label', '')
                        text = ''.join(elem.itertext()).strip()
                        if text:
                            if label:
                                parts.append(f"{label}: {text}")
                            else:
                                parts.append(text)
                    if parts:
                        abstract = ' '.join(parts)
                        self.logger.info(f"Successfully retrieved abstract from PubMed (PMID: {pmid})")
                        return abstract
                
                self.logger.warning(f"No abstract found in PubMed record (PMID: {pmid})")
            else:
                self.logger.warning(f"Could not find PMID for DOI {doi} or title")
            
        except Exception as e:
            self.logger.warning(f"Failed to get abstract from PubMed: {str(e)}")
        
        return None
    
    def _fetch_from_google_scholar(self, field_name: str, base_record: Dict) -> Optional[str]:
        """Get field value from Google Scholar (with improved timeout protection)"""
        try:
            # Search using title and authors
            query = base_record.get('title', '')
            if not query:
                return None
            
            # Add delay between requests to avoid rate limiting
            import threading
            import time
            
            if hasattr(self, '_last_scholar_request'):
                time_since_last = time.time() - self._last_scholar_request
                if time_since_last < 2.0:  
                    time.sleep(2.0 - time_since_last)
            
            self._last_scholar_request = time.time()
            
            result_container = [None]
            search_completed = [False]
            
            def search_worker():
                try:
                    search_query = scholarly.search_pubs(query)
                    pub = next(search_query, None)
                    
                    if pub and field_name in pub:
                        result_container[0] = str(pub[field_name])
                    
                    search_completed[0] = True
                except Exception as e:
                    self.logger.warning(f"Google Scholar field search failed: {str(e)}")
                    search_completed[0] = True
            
            # Start search thread
            search_thread = threading.Thread(target=search_worker)
            search_thread.daemon = True
            search_thread.start()
            
            # Wait up to 5 seconds with periodic checks (field completion is not critical)
            for _ in range(10):  # 10 * 0.5 = 5 seconds
                if search_completed[0]:
                    break
                time.sleep(0.5)
            
            if not search_completed[0]:
                self.logger.warning(f"Google Scholar field search timed out for {field_name}")
                return None
            
            return result_container[0]
                
        except Exception as e:
            self.logger.warning(f"Getting field {field_name} from Google Scholar failed: {str(e)}")
        
        return None


class FormatterModule:
    """Stage 4: Formatting and Generation Module."""
    
    def __init__(self):
        """Initialize the formatter module."""
        self.logger = logging.getLogger(__name__)
        
        # LaTeX character escape mapping for common Unicode characters
        self.unicode_to_latex = {
            'ä': r'{\"a}', 'Ä': r'{\"A}',
            'ë': r'{\"e}', 'Ë': r'{\"E}',
            'ï': r'{\"i}', 'Ï': r'{\"I}',
            'ö': r'{\"o}', 'Ö': r'{\"O}',
            'ü': r'{\"u}', 'Ü': r'{\"U}',
            'ÿ': r'{\"y}', 'Ÿ': r'{\"Y}',
            'á': r"{\'a}", 'Á': r"{\'A}",
            'é': r"{\'e}", 'É': r"{\'E}",
            'í': r"{\'i}", 'Í': r"{\'I}",
            'ó': r"{\'o}", 'Ó': r"{\'O}",
            'ú': r"{\'u}", 'Ú': r"{\'U}",
            'ý': r"{\'y}", 'Ý': r"{\'Y}",
            'à': r'{\`a}', 'À': r'{\`A}',
            'è': r'{\`e}', 'È': r'{\`E}',
            'ì': r'{\`i}', 'Ì': r'{\`I}',
            'ò': r'{\`o}', 'Ò': r'{\`O}',
            'ù': r'{\`u}', 'Ù': r'{\`U}',
            'â': r'{\^a}', 'Â': r'{\^A}',
            'ê': r'{\^e}', 'Ê': r'{\^E}',
            'î': r'{\^i}', 'Î': r'{\^I}',
            'ô': r'{\^o}', 'Ô': r'{\^O}',
            'û': r'{\^u}', 'Û': r'{\^U}',
            'ã': r'{\~a}', 'Ã': r'{\~A}',
            'ñ': r'{\~n}', 'Ñ': r'{\~N}',
            'õ': r'{\~o}', 'Õ': r'{\~O}',
            'å': r'{\aa}', 'Å': r'{\AA}',
            'ø': r'{\o}', 'Ø': r'{\O}',
            'æ': r'{\ae}', 'Æ': r'{\AE}',
            'œ': r'{\oe}', 'Œ': r'{\OE}',
            'ß': r'{\ss}',
            'ç': r'{\c{c}}', 'Ç': r'{\c{C}}',
            'ł': r'{\l}', 'Ł': r'{\L}',
            '–': '--',  # en-dash
            '—': '---',  # em-dash
            ''': "'", ''': "'",  # curly single quotes
            '"': '``', '"': "''",  # curly double quotes (non-ASCII)
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
            # Text already has LaTeX formatting, don't modify it
            # But still handle Unicode characters that aren't part of LaTeX commands
            # by only replacing characters that aren't inside {}
            return result
        
        # Replace Unicode characters with LaTeX equivalents
        for unicode_char, latex_escape in self.unicode_to_latex.items():
            result = result.replace(unicode_char, latex_escape)
        
        return result
    
    def format(self, completed_entries: List[CompletedEntry], 
               output_format: str) -> Dict[str, Any]:
        """Format completed records to the specified output format.

        Args:
            completed_entries: List of completed entries from
                :meth:`EnricherModule.enrich`.
            output_format: Desired citation style — ``"bibtex"``,
                ``"apa"``, or ``"mla"``.

        Returns:
            A dictionary with two keys:

            * ``results`` — a list of formatted citation strings.
            * ``report`` — a dict with ``total``, ``succeeded``, and
              ``failed_entries``.
        """
        self.logger.info(f"Starting to format {len(completed_entries)} entries to {output_format} format")
        
        formatted_strings = []
        failed_entries = []
        
        for entry in completed_entries:
            if entry['status'] == 'completed':
                try:
                    if output_format.lower() == 'bibtex':
                        formatted_string = self._format_bibtex(entry)
                    else:
                        raise FormatError(f"Unsupported output format: {output_format!r}. Only 'bibtex' is supported.")
                    
                    formatted_strings.append(formatted_string)
                    
                except Exception as e:
                    self.logger.error(f"Formatting entry {entry['id']} failed: {str(e)}")
                    failed_entries.append({
                        'id': entry['id'],
                        'error': str(e),
                        'doi': entry.get('doi', 'unknown')
                    })
            else:
                failed_entries.append({
                    'id': entry['id'],
                    'error': 'Entry processing failed',
                    'status': entry['status']
                })
        
        report = {
            'total': len(completed_entries),
            'succeeded': len(formatted_strings),
            'failed_entries': failed_entries
        }
        
        self.logger.info(f"Formatting completed: {len(formatted_strings)}/{len(completed_entries)} entries successful")
        
        return {
            'results': formatted_strings,
            'report': report
        }
    
    def _format_bibtex(self, entry: CompletedEntry) -> str:
        """Format to BibTeX using bibtexparser.dumps() for standards-compliant output."""
        bib_data = entry['bib_data']
        entry_type = bib_data.get('ENTRYTYPE', 'article')
        entry_id = bib_data.get('ID', entry['bib_key'])

        record = {'ENTRYTYPE': entry_type, 'ID': entry_id}
        for key, value in bib_data.items():
            if key not in ('ENTRYTYPE', 'ID') and value:
                value_str = str(value)
                if key in ('author', 'title', 'journal', 'publisher', 'note',
                           'booktitle', 'series', 'address', 'howpublished'):
                    record[key] = self._escape_latex_chars(value_str)
                else:
                    record[key] = value_str.strip('{}')

        db = bibtexparser.bibdatabase.BibDatabase()
        db.entries = [record]
        writer = bibtexparser.bwriter.BibTexWriter()
        writer.indent = '  '
        return bibtexparser.dumps(db, writer).strip()
    
