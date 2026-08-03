"""Tests for DOI-level deduplication in process output.

The same work commonly appears several times in a messy reference list under
different spellings (bare DOI, PMID, formatted citation). A normalization
layer must emit it once and report the repeats — re-emitting it under
suffixed cite keys just moves the mess into the output. All tests run
offline against the bundled fixtures.
"""

from unittest.mock import patch

from onecite import process_references
from onecite.benchmarks.offline import offline_requests_get

# Both fixtures resolve to LeCun/Bengio/Hinton, "Deep learning" (Nature 2015),
# DOI 10.1038/nature14539 — the bare DOI directly, the PMID via PubMed.
DEEP_LEARNING_DOI = "10.1038/nature14539"
DEEP_LEARNING_PMID = "PMID:26017442"


def _process(text):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return process_references(
            input_content=text,
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda _candidates: -1,
        )


def test_repeated_doi_is_emitted_once_and_reported():
    result = _process(f"{DEEP_LEARNING_DOI}\n\n{DEEP_LEARNING_DOI}")
    report = result["report"]
    assert len(result["results"]) == 1
    assert report["succeeded"] == 1
    assert len(report["duplicates"]) == 1
    duplicate = report["duplicates"][0]
    assert duplicate["id"] == 1
    assert duplicate["duplicate_of"] == 0
    assert duplicate["doi"] == DEEP_LEARNING_DOI
    assert duplicate["bib_key"]  # points at the emitted entry's cite key


def test_same_work_under_different_identifiers_is_deduplicated():
    # Bare DOI and PMID are different spellings of the same paper; the PMID
    # path resolves to the same DOI and must be merged, not double-emitted.
    result = _process(f"{DEEP_LEARNING_DOI}\n\n{DEEP_LEARNING_PMID}")
    report = result["report"]
    assert len(result["results"]) == 1
    assert report["succeeded"] == 1
    assert len(report["duplicates"]) == 1
    assert report["duplicates"][0]["duplicate_of"] == 0


def test_distinct_works_are_not_merged():
    result = _process(f"{DEEP_LEARNING_DOI}\n\n10.1038/nature14236")
    report = result["report"]
    assert len(result["results"]) == 2
    assert report["succeeded"] == 2
    assert report["duplicates"] == []


def test_duplicates_are_not_counted_as_failures():
    result = _process(f"{DEEP_LEARNING_DOI}\n\n{DEEP_LEARNING_DOI}")
    report = result["report"]
    assert report["failed_entries"] == []
