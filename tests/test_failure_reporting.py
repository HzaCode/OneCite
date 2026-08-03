"""Tests for auditable failure reporting.

A failed entry must carry the original input text and a reason code so that
a safely rejected identifier (fabricated DOI), an ambiguous reference (use
``onecite suggest``), and an unavailable source (retry) can be told apart —
they require different follow-up actions. All tests run offline against the
bundled fixtures.
"""

from unittest.mock import patch

from onecite import process_references
from onecite.benchmarks.offline import offline_requests_get
from onecite.pipeline import IdentifierModule


def _process(text):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return process_references(
            input_content=text,
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda _candidates: -1,
        )


def _single_failure(text):
    report = _process(text)["report"]
    assert report["succeeded"] == 0
    assert len(report["failed_entries"]) == 1
    return report["failed_entries"][0]


def test_fabricated_doi_reports_doi_not_found_with_raw_text():
    text = "10.9999/this.doi.does.not.exist"
    failed = _single_failure(text)
    assert failed["reason"] == "doi_not_found"
    assert failed["status"] == "identification_failed"
    assert failed["raw_text"] == text
    assert "fabricated or mistyped" in failed["error"]


def test_unverified_explicit_doi_cannot_fall_through_to_arxiv_substring():
    text = "10.1046/j.1365-313x.2001.01084.x.onecite-stress-114-b9d9c5ff"
    identifier = IdentifierModule()
    raw_entry = {"id": 0, "raw_text": text, "doi": text, "query_string": text}

    with patch.object(
        identifier,
        "_verify_doi_and_get_metadata",
        return_value=(None, "doi_not_found"),
    ):
        result = identifier._identify_single_entry(raw_entry)

    assert result["status"] == "identification_failed"
    assert result["failure_reason"] == "doi_not_found"
    assert result["doi"] is None
    assert result["arxiv_id"] is None


def test_explicit_doi_source_error_also_fails_closed():
    text = "10.1234/2001.01084"
    identifier = IdentifierModule()
    raw_entry = {"id": 0, "raw_text": text, "doi": text, "query_string": text}

    with patch.object(
        identifier,
        "_verify_doi_and_get_metadata",
        return_value=(None, "source_error"),
    ):
        result = identifier._identify_single_entry(raw_entry)

    assert result["status"] == "identification_failed"
    assert result["failure_reason"] == "source_error"
    assert result["arxiv_id"] is None


def test_zenodo_prefix_with_fabricated_suffix_cannot_truncate_to_real_record():
    text = "10.5281/zenodo.3233118.onecite-stress-1-deadbeef"
    identifier = IdentifierModule()
    raw_entry = {"id": 0, "raw_text": text, "doi": text, "query_string": text}

    with (
        patch.object(
            identifier,
            "_verify_doi_and_get_metadata",
            return_value=(None, "doi_not_found"),
        ),
        patch.object(identifier, "_extract_zenodo_info") as zenodo_fallback,
    ):
        result = identifier._identify_single_entry(raw_entry)

    assert result["status"] == "identification_failed"
    assert result["failure_reason"] == "doi_not_found"
    assert result["doi"] is None
    zenodo_fallback.assert_not_called()


def test_ambiguous_text_reports_no_strong_identifier_and_points_to_suggest():
    text = "Smith et al., neural networks for vision, 2019"
    failed = _single_failure(text)
    assert failed["reason"] == "no_strong_identifier"
    assert failed["status"] == "identification_failed"
    assert failed["raw_text"] == text
    assert "onecite suggest" in failed["error"]


def test_nonexistent_pmid_reports_pmid_unresolved():
    failed = _single_failure("PMID:99999999")
    assert failed["reason"] == "pmid_unresolved"
    assert failed["raw_text"] == "PMID:99999999"


def test_failure_reasons_distinguish_rejection_from_ambiguity():
    # One batch containing a fabricated DOI and an ambiguous reference must
    # produce two *different* reasons — this distinction is the point.
    text = "10.9999/fabricated.doi.2024\n\nan ambiguous plain text reference title"
    report = _process(text)["report"]
    reasons = {entry["reason"] for entry in report["failed_entries"]}
    assert reasons == {"doi_not_found", "no_strong_identifier"}


def test_raw_text_is_truncated_to_200_chars():
    long_text = "word " * 100  # 500 chars, no identifier
    failed = _single_failure(long_text.strip())
    assert len(failed["raw_text"]) <= 200
