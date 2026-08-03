#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Exception classes for OneCite."""


class OneCiteError(Exception):
    """Base exception for OneCite."""

    pass


class ValidationError(OneCiteError):
    """Citation data validation failed."""

    pass


class ParseError(OneCiteError):
    """Citation file parsing failed."""

    pass


class ResolverError(OneCiteError):
    """Identifier resolution failed."""

    pass


class FormatError(OneCiteError):
    """Citation formatting failed."""

    pass


class DataImportError(OneCiteError):
    """Citation data import failed."""

    pass


class ExportError(OneCiteError):
    """Citation data export failed."""

    pass
