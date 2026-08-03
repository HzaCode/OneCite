"""Embedded, explicitly labelled PMIDs must resolve like embedded DOIs.

A DOI embedded in citation text has always been extracted and resolved; an
explicitly labelled ``PMID:12345678`` embedded in the same kind of text is
just as unambiguous and must not be rejected as "no strong identifier".
Runs offline against the bundled fixtures (PMID 26017442 → LeCun 2015).
"""

from unittest.mock import patch

from onecite import process_references
from onecite.benchmarks.offline import offline_requests_get


def _process(text):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return process_references(
            input_content=text,
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
        )


def test_labelled_pmid_embedded_in_citation_text_resolves():
    result = _process("LeCun, Bengio & Hinton (2015). Deep learning. PMID:26017442")
    assert result["report"]["succeeded"] == 1
    assert "Deep learning" in result["results"][0]


def test_bare_pmid_block_still_resolves():
    result = _process("PMID:26017442")
    assert result["report"]["succeeded"] == 1


def test_bare_seven_digit_number_without_label_is_not_extracted_from_text():
    # An unlabelled number inside prose stays ambiguous — only the explicit
    # PMID label (or a bare-number block) is an identifier claim.
    result = _process("neural networks study 2601744 participants, 2019")
    assert result["report"]["succeeded"] == 0
    assert result["report"]["failed_entries"][0]["reason"] == "no_strong_identifier"


def test_labelled_but_nonexistent_pmid_reports_pmid_unresolved():
    result = _process("Some Author (2020). Fancy paper. PMID:99999999")
    failed = result["report"]["failed_entries"][0]
    assert failed["reason"] == "pmid_unresolved"
