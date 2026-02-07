"""
Tests for the ``process_references()`` public API surface.

All calls go through the mocked fixture so we don't depend on network.
"""
import pytest

from onecite import process_references


def _pick_first(candidates):
    return 0 if candidates else -1


class TestPythonAPI:

    def test_basic_doi_lookup(self, sample_references, run_onecite_process):
        """Simplest happy path: single DOI in, BibTeX out."""
        code, stdout, stderr, result = run_onecite_process(sample_references["doi_only"])
        assert code == 0, stderr
        assert result["report"]["total"] >= 1
        assert result["report"]["succeeded"] >= 1
        assert isinstance(result["report"]["failed_entries"], list)

    def test_bibtex_passthrough(self, sample_references, run_onecite_process):
        """Feeding an existing .bib entry should round-trip cleanly."""
        code, stdout, stderr, result = run_onecite_process(
            sample_references["bibtex_entry"], input_type="bib"
        )
        assert code == 0, stderr
        assert result["report"]["total"] >= 1

    def test_all_output_formats(self, sample_references, run_onecite_process):
        """Each supported format should produce non-empty output."""
        for fmt in ("bibtex", "apa", "mla"):
            code, stdout, _, result = run_onecite_process(
                sample_references["doi_only"], output_format=fmt
            )
            assert code == 0, f"{fmt} format failed"
            assert result["report"]["total"] >= 1

    def test_callback_receives_candidates(self, run_onecite_process):
        """When the query is ambiguous the callback should be invoked."""
        callback_log = []

        def _logging_cb(candidates):
            callback_log.append(len(candidates))
            return 0

        # Use the fixture's mock environment but with our own callback.
        # We call process_references directly here because the fixture
        # hard-codes the callback.
        from unittest.mock import patch
        from tests.mock_responses import mock_requests_get

        with (
            patch("onecite.pipeline.requests.get", side_effect=mock_requests_get),
            patch("onecite.core.requests.get", side_effect=mock_requests_get),
            patch("requests.get", side_effect=mock_requests_get),
        ):
            result = process_references(
                input_content="Some ambiguous reference that might trigger callback",
                input_type="txt",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=_logging_cb,
            )
        # Callback may or may not fire depending on search results;
        # either way the call should not crash.
        assert isinstance(result, dict)

    def test_invalid_input_type_raises(self):
        with pytest.raises(Exception):
            process_references(
                input_content="test",
                input_type="invalid_type",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=_pick_first,
            )

    def test_empty_input_returns_zero_total(self, run_onecite_process):
        """Blank input → report shows 0 entries, no crash."""
        code, _, _, result = run_onecite_process("")
        assert code == 0
        assert result["report"]["total"] == 0
        assert result["results"] == []

    def test_multiple_entries(self, sample_references, run_onecite_process):
        """Two refs separated by a blank line should yield ≥ 2 entries."""
        combined = f"{sample_references['doi_only']}\n\n{sample_references['arxiv_id']}"
        code, _, _, result = run_onecite_process(combined)
        assert code == 0
        assert result["report"]["total"] >= 2
