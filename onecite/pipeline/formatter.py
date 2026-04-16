# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 4 — format completed entries into BibTeX output."""

import logging
import re
from typing import List, Dict, Any

import bibtexparser

from ..core import CompletedEntry
from ..exceptions import FormatError


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
            output_format: Output format. Only ``"bibtex"`` is
                supported; any other value raises ``FormatError``.

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
