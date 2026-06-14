"""Quick sanity checks for the public Python API.

These run against the real network, so they're marked ``live`` and skipped
by default. For fully-mocked equivalents see ``test_python_api.py``.
"""

import pytest

from onecite import process_references

pytestmark = pytest.mark.live


def _auto_pick(candidates):
    """Process smoke tests should not rely on candidate guessing."""
    return -1


def test_readme_example():
    """Make sure the snippet we show in README.md keeps working."""
    result = process_references(
        input_content="10.1038/nature14539\n\narXiv:1706.03762",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=_auto_pick,
    )
    assert isinstance(result, dict)
    assert result.get("results"), "Expected at least one formatted entry"
    assert "report" in result
