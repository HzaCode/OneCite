#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command-line interface for OneCite.
"""

import argparse
import sys
import os
from typing import Optional, List, Dict

from .core import process_references
from .exceptions import OneCiteError
from . import __version__


def main() -> int:
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        if args.command == 'process':
            return process_command(args)
        elif args.command == 'version':
            print(f"OneCite version {__version__}")
            return 0
        else:
            parser.print_help()
            return 1
            
    except OneCiteError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Processing failed: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='onecite',
        description='Citation management and academic reference toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  onecite process references.txt --output-format bibtex
  onecite process references.bib --input-type bib --template conference_paper
  onecite process references.txt --interactive --output results.bib
  onecite process "10.1038/nature14539"
  onecite process "attention is all you need, Vaswani et al., NIPS 2017"
  echo "10.1038/nature14539" | onecite process -
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Main processing command
    process_parser = subparsers.add_parser(
        'process',
        help='Process references through the OneCite pipeline'
    )
    process_parser.add_argument(
        'input_file',
        help='Input file, "-" for stdin, or a reference string (e.g. a DOI or title)'
    )
    process_parser.add_argument(
        '--input-type',
        choices=['txt', 'bib'],
        default='txt',
        help='Input type (default: txt)'
    )
    process_parser.add_argument(
        '--template',
        default='journal_article_full',
        help='Template to use (default: journal_article_full)'
    )
    process_parser.add_argument(
        '--output-format',
        choices=['bibtex', 'apa', 'mla'],
        default='bibtex',
        help='Output format (default: bibtex)'
    )
    process_parser.add_argument(
        '--output',
        '-o',
        help='Output file (default: stdout)'
    )
    process_parser.add_argument(
        '--interactive',
        action='store_true',
        help='Enable interactive mode for ambiguous matches'
    )
    process_parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Suppress verbose logging output'
    )
    process_parser.add_argument(
        '--google-scholar',
        action='store_true',
        default=False,
        help='Enable Google Scholar as an additional data source (requires scholarly package)'
    )
    
    return parser


def process_command(args: "argparse.Namespace") -> int:
    """Run the ``onecite process`` subcommand.

    Args:
        args: Parsed command-line arguments from
            :func:`create_parser`.

    Returns:
        Exit code — ``0`` on success, ``1`` on failure.
    """
    try:
        if args.input_file == '-':
            input_content = sys.stdin.read()
        elif os.path.exists(args.input_file):
            with open(args.input_file, 'r', encoding='utf-8') as f:
                input_content = f.read()
            if args.input_type == 'txt' and args.input_file.lower().endswith('.bib'):
                args.input_type = 'bib'
        else:
            input_content = args.input_file
        
        def interactive_callback(candidates: List[Dict]) -> int:
            if not args.interactive:
                # Non-interactive mode, skip all candidates
                return -1
            
            print("Found multiple possible matches:")
            for i, candidate in enumerate(candidates):
                print(f"{i + 1}. {candidate.get('title', 'Unknown')}")
                print(f"   Authors: {', '.join(candidate.get('authors', []))}")
                print(f"   Journal: {candidate.get('journal', 'Unknown')}")
                print(f"   Year: {candidate.get('year', 'Unknown')}")
                print(f"   Match Score: {candidate.get('match_score', 0)}")
                print()
            
            while True:
                try:
                    choice = input("Please select (1-{}, 0=skip): ".format(len(candidates)))
                    choice_num = int(choice)
                    if choice_num == 0:
                        return -1  # Skip
                    elif 1 <= choice_num <= len(candidates):
                        return choice_num - 1
                    else:
                        print("Invalid selection, please try again")
                except (ValueError, KeyboardInterrupt):
                    print("Operation cancelled")
                    return -1
        
        if args.quiet:
            import logging
            logging.basicConfig(level=logging.CRITICAL)
            for logger_name in ['onecite', 'scholarly', 'httpx', 'fake_useragent']:
                logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        
        result = process_references(
            input_content=input_content,
            input_type=args.input_type,
            template_name=args.template,
            output_format=args.output_format,
            interactive_callback=interactive_callback,
            use_google_scholar=args.google_scholar,
        )
        
        output_content = '\n\n'.join(result['results'])
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            if not args.quiet:
                print(f"Results saved to: {args.output}")
        else:
            print(output_content)
        
        if not args.quiet:
            report = result['report']
            print(f"\nProcessing Report:")
            print(f"  Total entries: {report['total']}")
            print(f"  Successfully processed: {report['succeeded']}")
            print(f"  Failed entries: {len(report['failed_entries'])}")
            
            if report['failed_entries']:
                print(f"\nFailed entries:")
                for failed in report['failed_entries']:
                    print(f"  - Entry {failed['id']}: {failed.get('error', 'Unknown error')}")
        
        return 0
        
    except Exception as e:
        print(f"Processing failed: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
