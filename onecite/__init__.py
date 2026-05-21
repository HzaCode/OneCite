#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OneCite: Citation Management and Academic Reference Toolkit

A Python package for managing bibliographic data and generating
citations in multiple formats.
"""

__version__ = "0.1.1"
__author__ = "OneCite Team"
__email__ = "ang@hezhiang.com"
__license__ = "MIT"

from .core import (
    RawEntry,
    IdentifiedEntry,
    CompletedEntry,
    TemplateLoader,
    PipelineController,
    process_references,
)

from .benchmark import (
    format_benchmark_text,
    load_benchmark_suite,
    run_benchmark,
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
    # Benchmarking
    "format_benchmark_text",
    "load_benchmark_suite",
    "run_benchmark",
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
__description__ = "Citation management and academic reference toolkit"
__url__ = "https://github.com/HzaCode/OneCite"
