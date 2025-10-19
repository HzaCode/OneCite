#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exception classes for OneCite package.
"""


class OneCiteError(Exception):
    """
    Base exception class for all OneCite errors.
    
    This is the parent class for all custom exceptions in the OneCite package.
    """
    pass


class ValidationError(OneCiteError):
    """
    Raised when citation data validation fails.
    
    This exception is raised when citation data doesn't meet required
    formatting or completeness standards.
    """
    pass


class ParseError(OneCiteError):
    """
    Raised when parsing citation files fails.
    
    This exception is raised when BibTeX, RIS, or other citation format
    files cannot be properly parsed.
    """
    pass


class ResolverError(OneCiteError):
    """
    Raised when DOI or other identifier resolution fails.
    
    This exception is raised when external services (like CrossRef)
    cannot resolve identifiers to citation metadata.
    """
    pass


class FormatError(OneCiteError):
    """
    Raised when citation formatting fails.
    
    This exception is raised when citations cannot be formatted
    in the requested style.
    """
    pass


class ImportError(OneCiteError):
    """
    Raised when importing citation data fails.
    
    This exception is raised when citation files cannot be imported
    due to format or access issues.
    """
    pass


class ExportError(OneCiteError):
    """
    Raised when exporting citation data fails.
    
    This exception is raised when citations cannot be exported
    to the requested format or location.
    """
    pass
