#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OneCite: Auditable citation normalization for research workflows.

A command-line and Python toolkit that normalizes messy, mixed-format
scholarly references (DOIs, PMIDs, arXiv IDs, ISBNs, URLs, BibTeX fragments)
into auditable, source-resolved BibTeX and CSL-JSON. Strong identifiers follow
documented metadata-service routes via ``process``; ambiguous plain-text
references are returned as candidates via ``suggest`` and are not auto-promoted.
"""

__version__ = "0.2.0"
__author__ = "He Zhiang"
__email__ = "ang@hezhiang.com"
__license__ = "MIT"

from .core import (
    RawEntry,
    IdentifiedEntry,
    CompletedEntry,
    TemplateLoader,
    PipelineController,
    process_references,
    suggest_references,
)

from .benchmark import (
    format_benchmark_text,
    load_benchmark_suite,
    run_benchmark,
)

from .benchmarks.anti_hallucination import (
    format_anti_hallucination_text,
    run_anti_hallucination_eval,
)

from .exceptions import (
    OneCiteError,
    ValidationError,
    ParseError,
    ResolverError,
)

__all__ = [
    # Core data structures
    "RawEntry",
    "IdentifiedEntry",
    "CompletedEntry",
    # Core classes
    "TemplateLoader",
    "PipelineController",
    # Main API
    "process_references",
    "suggest_references",
    # Benchmarking
    "format_benchmark_text",
    "load_benchmark_suite",
    "run_benchmark",
    # Anti-hallucination evaluation
    "run_anti_hallucination_eval",
    "format_anti_hallucination_text",
    # Exceptions
    "OneCiteError",
    "ValidationError",
    "ParseError",
    "ResolverError",
    # Metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]

# Package metadata
__title__ = "onecite"
__description__ = "Auditable normalization into source-resolved BibTeX and CSL-JSON"
__url__ = "https://github.com/HzaCode/OneCite"
