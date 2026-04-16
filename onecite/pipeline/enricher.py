# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 3 — enrich identified entries with external metadata."""

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
