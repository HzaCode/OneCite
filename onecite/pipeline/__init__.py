# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""OneCite's 4-stage processing pipeline.

Historically this lived in a single ``pipeline.py`` of ~3000 lines.  It was
split per pyOpenSci review issue #17 into one module per stage.  All public
symbols are re-exported here so callers and tests that do

    from onecite.pipeline import IdentifierModule
    import onecite.pipeline as pm  # and then: patch("onecite.pipeline.requests.get", ...)

keep working unchanged.
"""

# Keep ``requests`` at package level so that tests which do
# ``patch("onecite.pipeline.requests.get", ...)`` resolve the attribute
# correctly.  Because Python caches modules, this is the same ``requests``
# module object that all sub-modules import — so the patch reaches them too.
import requests  # noqa: F401

from ._utils import _safe_year
from .parser import ParserModule
from .identifier import IdentifierModule
from .enricher import EnricherModule
from .formatter import FormatterModule

__all__ = [
    "ParserModule",
    "IdentifierModule",
    "EnricherModule",
    "FormatterModule",
    "_safe_year",
]
