# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 2 — identify entries and standardise them into ``IdentifiedEntry``."""

import re
import os
import logging
import time
import urllib.parse
from html import unescape
from typing import List, Dict, Optional, Callable, Any

import requests
from bs4 import BeautifulSoup
import bibtexparser
from thefuzz import fuzz

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

from ..core import RawEntry, IdentifiedEntry, CompletedEntry
from ..exceptions import ParseError, ResolverError, ValidationError, FormatError
from ._utils import _safe_year


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
    
    def _is_datacite_doi(self, doi: str) -> bool:
        """Check if DOI is registered with DataCite (not CrossRef)."""
        datacite_prefixes = [
            '10.5281/',   # Zenodo
            '10.6084/',   # Figshare
            '10.5061/',   # Dryad
            '10.6078/',   # DataONE
            '10.7910/',   # DVN/Dataverse
            '10.13003/',  # RePEc
            '10.14291/',  # UBC Dataverse
            '10.5683/',   # Scholars Portal
            '10.20382/',  # University of Manitoba Dataverse
            '10.5680/',   # University of Sheffield
            '10.25739/',  # Griffith University
        ]
        return any(doi.startswith(prefix) for prefix in datacite_prefixes)

    def _verify_doi_and_get_metadata(self, doi: str) -> Optional[Dict]:
        """Verify DOI exists in Crossref or DataCite and get real metadata for comparison."""
        # Try CrossRef first (covers most academic journals/papers)
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
                # Try DataCite for dataset/software DOIs
                if self._is_datacite_doi(doi):
                    self.logger.info(f"DOI {doi} appears to be DataCite, trying DataCite API...")
                    datacite_result = self._query_datacite(doi)
                    if datacite_result:
                        return datacite_result
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
        """Perform fuzzy search using simplified routing: always query core sources, conditionally append specialized sources."""
        query_string = raw_entry['query_string']
        query_lower = query_string.lower()
        
        candidates = []
        
        # === Core sources: always query ===
        # CrossRef covers most academic papers; Semantic Scholar adds citations/automation metadata
        self.logger.info("Querying core sources: CrossRef + Semantic Scholar")
        crossref_results = self._search_crossref(query_string)
        candidates.extend(crossref_results)
        
        semantic_results = self._search_semantic_scholar(query_string)
        candidates.extend(semantic_results)
        
        # === Conditional specialized sources ===
        
        # 1. PMID pattern detected
        pmid_match = re.match(r'^(PMID:?\s*)?(\d{7,8})$', query_string.strip())
        if pmid_match:
            pmid = pmid_match.group(2)
            self.logger.info(f"Detected PubMed ID pattern: {pmid}, querying PubMed")
            pubmed_result = self._search_pubmed_by_id(pmid)
            if pubmed_result:
                # For PMID-only queries (no other text), return directly
                # This handles cases where the query is just "PMID:12345678"
                text_without_pmid = query_string.replace(f"PMID:{pmid}", "").replace(pmid, "").strip()
                if len(text_without_pmid) < 3:  # Essentially just the PMID
                    return {
                        'id': raw_entry['id'],
                        'raw_text': raw_entry['raw_text'],
                        'doi': pubmed_result.get('doi'),
                        'arxiv_id': None,
                        'url': pubmed_result.get('url'),
                        'metadata': pubmed_result,
                        'status': 'identified'
                    }
                # Otherwise, add to candidates for scoring alongside other sources
                candidates.append(pubmed_result)
        
        # 2. Strong biomedical cues → also query PubMed (as additive source)
        strong_medical_cues = ['pubmed', 'pmid', 'clinical trial', 'randomized controlled']
        if any(cue in query_lower for cue in strong_medical_cues):
            self.logger.info("Strong medical cues detected, querying PubMed as additive source")
            pubmed_results = self._search_pubmed(query_string)
            candidates.extend(pubmed_results)
        
        # 3. Book indicators → query Google Books
        # Simplified detection: only check strongest signals
        has_isbn = bool(re.search(r'isbn[:\s]*[\d\-xX]{10,17}', query_lower, re.IGNORECASE))
        has_edition = bool(re.search(r'\b\d+(?:st|nd|rd|th)?\s+ed\.?\b', query_lower))
        has_book_publisher = any(pub in query_lower for pub in ['wiley', "o'reilly", 'springer', 'cambridge press', 'mit press'])
        
        if has_isbn or has_edition or has_book_publisher:
            self.logger.info(f"Book indicators detected (ISBN={has_isbn}, edition={has_edition}, publisher={has_book_publisher}), querying Google Books")
            books_results = self._search_google_books(query_string)
            candidates.extend(books_results)
        
        # 4. Thesis indicators → query external providerRE/BASE
        thesis_keywords = ['dissertation', 'phd thesis', 'master thesis', 'doctoral thesis', 'thesis']
        if any(kw in query_lower for kw in thesis_keywords):
            self.logger.info("Thesis indicators detected, querying external providerRE/BASE")
            thesis_results = self._search_openaire_for_thesis(query_string) or self._search_base_for_thesis(query_string)
            if thesis_results:
                candidates.append(thesis_results)
        
        # 5. Google Scholar as optional fallback (if enabled and core sources returned little)
        if self.use_google_scholar:
            if len(crossref_results) == 0 and len(semantic_results) == 0:
                self.logger.info("Core sources returned no results, trying Google Scholar")
                scholar_results = self._search_google_scholar(query_string)
                candidates.extend(scholar_results)
        
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
        # _score_candidates now handles tie-breaking internally
        best_candidate = scored_candidates[0] if scored_candidates else None
        
        if not best_candidate:
            self.logger.warning(f"Entry {raw_entry['id']}: no scored candidates")
            return {
                'id': raw_entry['id'],
                'raw_text': raw_entry['raw_text'],
                'doi': None,
                'arxiv_id': None,
                'url': None,
                'metadata': {},
                'status': 'identification_failed'
            }
        
        # Try to resolve DOI for strong matches without one
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
        
        # Low confidence fallback: unified threshold
        # With two-layer scoring, match_score is purely about query relevance
        LOW_CONFIDENCE_THRESHOLD = 50
        if best_candidate['match_score'] >= LOW_CONFIDENCE_THRESHOLD and best_candidate.get('title'):
            self.logger.info(f"Entry {raw_entry['id']} adopting best candidate with score {best_candidate['match_score']}")
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
        """Score candidates using two-layer scoring: Query-Match Score + Tie-Break."""
        scored_candidates = []

        # Normalize query for title matching
        normalized_query = query_string.strip()
        # Try to derive a probable title part: cut at first 4-digit year
        title_part = re.split(r'\b(19|20)\d{2}\b', normalized_query)[0].strip() or normalized_query
        # Remove common "et al." noise
        title_part = re.sub(r'\bet\s*al\.?\b', '', title_part, flags=re.IGNORECASE).strip()

        # Venue synonyms for query normalization only (not scoring)
        synonyms = {
            'nips': 'neural information processing systems',
            'neurips': 'neural information processing systems',
            'cvpr': 'computer vision and pattern recognition',
            'iclr': 'international conference on learning representations',
            'icml': 'international conference on machine learning',
        }

        normalized_query_lower = normalized_query.lower()
        # Expand query with venue synonyms for better matching
        for k, v in synonyms.items():
            if k in normalized_query_lower and v not in normalized_query_lower:
                normalized_query += f" {v}"
                normalized_query_lower = normalized_query.lower()

        # Normalize candidate venue names
        def normalize_venue(venue):
            if not venue:
                return ""
            venue_lower = venue.lower()
            for k, v in synonyms.items():
                if k in venue_lower:
                    return venue.replace(k, v).replace(k.upper(), v)
            return venue

        query_year = None
        has_query_year = False
        year_match = re.search(r'\b(19|20)\d{2}\b', normalized_query)
        if year_match:
            query_year = int(year_match.group(0))
            has_query_year = True

        # Check if query contains venue hints
        has_venue_in_query = any(syn in normalized_query_lower for syn in synonyms.keys()) or \
                            any(journal_word in normalized_query_lower for journal_word in ['journal', 'proceedings', 'conference', 'transactions'])

        # Dynamic weight calculation based on available query signals
        # If a signal is missing, redistribute its weight to other signals
        available_signals = ['title', 'author']  # Always available
        if has_query_year:
            available_signals.append('year')
        if has_venue_in_query:
            available_signals.append('venue')

        # Base weights (will be normalized)
        base_weights = {'title': 0.55, 'author': 0.25, 'year': 0.15, 'venue': 0.10}

        # Normalize weights for available signals
        available_weight_sum = sum(base_weights[s] for s in available_signals)
        weights = {s: base_weights[s] / available_weight_sum for s in available_signals}

        for candidate in candidates:
            scores = {}

            # Title similarity (core signal)
            candidate_title = candidate.get('title', '').lower()
            base_title = title_part.lower()
            title_score = 0
            if candidate_title and base_title:
                ratio = fuzz.ratio(base_title, candidate_title)
                partial = fuzz.partial_ratio(base_title, candidate_title)
                token_sort = fuzz.token_sort_ratio(base_title, candidate_title)
                token_set = fuzz.token_set_ratio(base_title, candidate_title)
                title_score = max(ratio, partial, token_sort, token_set)
                # Bonus for exact phrase match
                if base_title in candidate_title or candidate_title in base_title:
                    title_score = min(title_score + 10, 100)
            scores['title'] = title_score

            # Author matching
            author_score = 0
            if candidate.get('authors'):
                authors_text = ' '.join(candidate['authors']).lower()
                query_lower = normalized_query.lower()
                exact_match = any(author.lower().strip() in query_lower for author in candidate['authors'])
                if exact_match:
                    author_score = 80
                else:
                    author_score = fuzz.partial_ratio(query_lower, authors_text)
            scores['author'] = author_score

            # Year matching (only if query has year)
            year_score = 0
            if has_query_year and candidate.get('year'):
                try:
                    candidate_year = int(candidate['year'])
                    year_diff = abs(candidate_year - query_year)
                    if year_diff == 0:
                        year_score = 100
                    elif year_diff <= 2:
                        year_score = 70
                    elif year_diff <= 5:
                        year_score = 30
                except (ValueError, TypeError):
                    pass
            scores['year'] = year_score

            # Venue matching (only if query has venue hint)
            venue_score = 0
            venue_lower = ""
            if candidate.get('journal'):
                normalized_venue = normalize_venue(candidate['journal'])
                venue_lower = normalized_venue.lower()
                if has_venue_in_query:
                    if venue_lower and venue_lower in normalized_query_lower:
                        venue_score = 80  # Exact venue mention
                    else:
                        venue_score = fuzz.partial_ratio(normalized_query_lower, venue_lower)
            scores['venue'] = venue_score

            # Compute Query-Match Score (0-100)
            match_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in available_signals)
            match_score = min(max(match_score, 0), 100)

            # Store for tie-break layer
            candidate_copy = candidate.copy()
            candidate_copy['match_score'] = round(match_score, 2)
            candidate_copy['score_breakdown'] = scores
            candidate_copy['_weights'] = weights  # Internal use for debugging
            scored_candidates.append(candidate_copy)

        # Sort by match score descending
        scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)

        # Tie-Break Layer: when top-2 scores are close (within 5 points)
        if len(scored_candidates) >= 2:
            best = scored_candidates[0]
            second = scored_candidates[1]
            if best['match_score'] - second['match_score'] <= 5:
                # Apply tie-break criteria
                def tie_break_rank(c):
                    sb = c.get('score_breakdown', {})
                    rank = 0
                    # 1. Exact title match (highest priority)
                    if sb.get('title', 0) >= 90:
                        rank += 1000
                    # 2. Venue exact hit
                    if sb.get('venue', 0) >= 70:
                        rank += 100
                    # 3. Has DOI
                    if c.get('doi'):
                        rank += 10
                    # 4. Source tier (lower number = better)
                    source_tier = {
                        'crossref': 1, 'pubmed': 2, 'semantic_scholar': 3,
                        'google_books': 4, 'datacite': 5, 'zenodo': 6, 'google_scholar': 7
                    }.get(c.get('source'), 8)
                    rank -= source_tier  # Better source = lower tier number = higher rank
                    return rank

                # Re-sort with tie-break
                scored_candidates.sort(key=lambda x: (x['match_score'], tie_break_rank(x)), reverse=True)

        return scored_candidates
