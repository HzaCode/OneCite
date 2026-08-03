"""Round-trip idempotence: OneCite's own BibTeX output must survive
re-processing through ``input_type="bib"`` byte-identically.

This is the direct test of the "reproducible" claim — and it caught two
real defects: bibtexparser silently drops non-standard entry types
(@software), so OneCite could not re-parse its own software entries; and a
non-empty bib file that parsed to zero entries produced an empty "success"
instead of an error. All tests run offline against bundled fixtures.
"""

import pytest
from unittest.mock import patch

from onecite import process_references
from onecite.exceptions import ParseError
from onecite.benchmarks.offline import offline_requests_get


def _run(content, input_type):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return process_references(
            input_content=content,
            input_type=input_type,
            template_name="journal_article_full",
            output_format="bibtex",
        )


@pytest.mark.parametrize(
    "identifier",
    [
        "10.1038/nature14236",  # journal article via CrossRef
        "https://github.com/HzaCode/OneCite",  # @software entry
        "1706.03762",  # arXiv preprint
        "10.5281/zenodo.3233118",  # Zenodo dataset (@misc)
    ],
)
def test_own_output_round_trips_byte_identically(identifier):
    first = _run(identifier, "txt")
    assert first["report"]["succeeded"] == 1
    bibtex_once = first["results"][0]

    second = _run(bibtex_once, "bib")
    assert second["report"]["succeeded"] == 1, second["report"]["failed_entries"]
    assert second["results"][0] == bibtex_once


def test_software_entry_type_is_not_dropped_by_bib_parser():
    software_entry = (
        "@software{onecite2026,\n"
        "  title = {OneCite},\n"
        "  author = {HzaCode},\n"
        "  year = {2026},\n"
        "  url = {https://github.com/HzaCode/OneCite}\n"
        "}"
    )
    result = _run(software_entry, "bib")
    # The entry must at least be *seen* (total 1), not silently dropped.
    assert result["report"]["total"] == 1


def test_unparseable_bib_content_raises_instead_of_empty_success():
    # A non-empty file yielding zero entries must error loudly — an empty
    # "success" silently loses the user's data.
    with pytest.raises(ParseError):
        _run("this is not bibtex at all { } @", "bib")


def test_doi_verification_response_is_reused_not_refetched():
    # Identify verifies the DOI against CrossRef and already holds the full
    # work object; enrichment must reuse it instead of issuing a second
    # identical API call (which doubles load and latency per entry).
    calls = []

    def counting_get(url, *args, **kwargs):
        calls.append(url)
        return offline_requests_get(url, *args, **kwargs)

    with patch.multiple("onecite.pipeline.requests", get=counting_get):
        result = process_references(
            input_content="10.1038/nature14236",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
        )
    assert result["report"]["succeeded"] == 1
    crossref_calls = [url for url in calls if "crossref" in url]
    assert len(crossref_calls) == 1, crossref_calls
