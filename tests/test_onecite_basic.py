"""Quick sanity checks for the public Python API.

These run against the real network, so they're skipped when the ``--offline``
marker is active.  For fully-mocked equivalents see ``test_python_api.py``.
"""
from onecite import process_references


def _auto_pick(candidates):
    """Always pick the first candidate – good enough for smoke tests."""
    return 0 if candidates else -1


def test_readme_example():
    """Make sure the snippet we show in README.md keeps working."""
    result = process_references(
        input_content="10.1038/nature14539\n\nAttention is all you need\nVaswani et al.\nNIPS 2017",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=_auto_pick,
    )
    assert isinstance(result, dict)
    assert result.get("results"), "Expected at least one formatted entry"
    assert "report" in result


def test_apa_output():
    """APA is the second-most requested format after BibTeX."""
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="apa",
        interactive_callback=_auto_pick,
    )
    assert result.get("results")
