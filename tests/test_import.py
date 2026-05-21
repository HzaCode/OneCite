"""Smoke-test that the public surface is importable.

Kept deliberately minimal – the heavy API tests live in
``test_python_api.py`` and ``test_onecite_basic.py``.
"""

import pytest


def test_process_references_importable():
    """Guard against accidental circular-import breakage."""
    from onecite import process_references

    assert callable(process_references)


def test_streamlit_optional():
    """streamlit is an optional visualisation dep; we don't want CI to
    fail when it's not installed."""
    pytest.importorskip("streamlit")
