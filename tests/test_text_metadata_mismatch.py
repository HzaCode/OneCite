"""Tests for the text/DOI mismatch warning (hallucinated title+DOI pairing).

A real-but-wrong DOI pasted next to a different paper's title is the most
common shape of a hallucinated citation. OneCite still resolves the DOI (the
identifier stays authoritative) but must surface a non-blocking warning
instead of silently emitting the wrong work as verified output. These tests
run fully offline against the bundled fixtures.
"""

from unittest.mock import patch

from onecite import process_references
from onecite.benchmarks.offline import offline_requests_get
from onecite.pipeline.identifier import IdentifierModule

# Fixture DOI 10.1038/nature14236 resolves to Mnih et al.,
# "Human-level control through deep reinforcement learning" (Nature 2015).
DQN_DOI = "10.1038/nature14236"


def _process(text):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return process_references(
            input_content=text,
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda _candidates: -1,
        )


def test_mismatched_title_and_doi_resolves_with_warning():
    result = _process(f"Attention Is All You Need. Vaswani, A. et al. (2017). doi:{DQN_DOI}")
    report = result["report"]
    assert report["succeeded"] == 1  # DOI stays authoritative — still resolves
    assert len(report["warnings"]) == 1
    warning = report["warnings"][0]
    assert warning["id"] == 0
    assert warning["type"] == "text_metadata_mismatch"
    assert warning["resolved_doi"] == DQN_DOI
    assert "Human-level control" in warning["resolved_title"]
    assert warning["similarity"] < 45


def test_consistent_title_and_doi_resolves_without_warning():
    result = _process(
        "Human-level control through deep reinforcement learning. "
        f"Mnih, V. et al. Nature 518, 529-533 (2015). doi:{DQN_DOI}"
    )
    report = result["report"]
    assert report["succeeded"] == 1
    assert report["warnings"] == []


def test_bare_doi_has_no_warning():
    result = _process(DQN_DOI)
    report = result["report"]
    assert report["succeeded"] == 1
    assert report["warnings"] == []


def test_journal_volume_noise_alone_does_not_trigger_warning():
    # Journal name, volume, pages, and year carry no title signal; a citation
    # written as "Nature 518, 529-533 (2015). doi:..." must not be flagged.
    result = _process(f"Nature 518, 529-533 (2015). doi:{DQN_DOI}")
    report = result["report"]
    assert report["succeeded"] == 1
    assert report["warnings"] == []


def test_short_title_with_year_conflict_is_flagged():
    # "Deep learning" is only two tokens; a random ML-word soup sharing the
    # word "learning" can pass the base similarity threshold. A year cited
    # far from the resolved metadata's year is independent mismatch
    # evidence and must trigger the flag anyway.
    result = _process(
        "Learning Quantum Inference Hyperbolic Modular. Author, A. et al. (1997). "
        "doi:10.1038/nature14539"
    )
    report = result["report"]
    assert report["succeeded"] == 1
    assert len(report["warnings"]) == 1
    assert report["warnings"][0]["year_conflict"] is True


def test_short_author_journal_citation_with_year_conflict_is_flagged():
    # Three descriptive words would normally be below the comparison gate,
    # but a cited year decades away from the DOI metadata is independent
    # contradictory evidence and must not be silently ignored.
    result = _process(f"Hafez E. J Reprod Fertil. 2, 163 (1961). doi:{DQN_DOI}")
    report = result["report"]
    assert report["succeeded"] == 1
    assert len(report["warnings"]) == 1
    assert report["warnings"][0]["type"] == "text_metadata_mismatch"
    assert report["warnings"][0]["year_conflict"] is True


def test_zero_overlap_text_with_nearby_year_is_flagged():
    # Found by randomized robustness round 96 (seed 90096): descriptive text
    # sharing no words with the resolved title slipped past the character
    # fuzz threshold when the cited year was close enough to avoid the year
    # check. Positive title/author overlap is required — fuzz alone is not
    # evidence.
    result = _process(
        "Stochastic Hyperbolic Riemannian Propagation Convex. Author, A. et al. (2012). "
        "doi:10.1038/nature14539"
    )
    report = result["report"]
    assert report["succeeded"] == 1
    assert len(report["warnings"]) == 1
    assert report["warnings"][0]["type"] == "text_metadata_mismatch"


def test_author_only_citation_with_matching_authors_is_not_flagged():
    # A citation that names the right authors but paraphrases the title must
    # not be flagged — author family-name coverage is accepted as evidence.
    result = _process(
        "LeCun, Yann, Bengio, Yoshua and Hinton, Geoffrey. Nature 521, 436-444 (2015). "
        "doi:10.1038/nature14539"
    )
    report = result["report"]
    assert report["succeeded"] == 1
    assert report["warnings"] == []


def test_correct_short_title_with_correct_year_is_not_flagged():
    result = _process(
        "Deep learning. LeCun, Bengio & Hinton. Nature (2015). doi:10.1038/nature14539"
    )
    report = result["report"]
    assert report["succeeded"] == 1
    assert report["warnings"] == []


def test_sparse_correct_citation_with_matching_coordinates_is_not_flagged():
    metadata = {
        "doi": "10.1029/97je03136",
        "title": (
            "Potential anomalies on a sphere: Applications to the thickness " "of the lunar crust"
        ),
        "authors": ["Mark A. Wieczorek", "Roger J. Phillips"],
        "year": 1998,
        "journal": "Journal of Geophysical Research: Planets",
        "volume": "103",
        "pages": "1715-1724",
    }
    citation = (
        "M.A. Wieczoreck, R.J. Phillips, J. Geophys. Res. 103(E1), "
        "1715-1724 (1998) DOI: 10.1029/97je03136"
    )

    warning = IdentifierModule()._check_text_metadata_mismatch(
        citation, "10.1029/97je03136", metadata
    )

    assert warning is None


def test_sparse_matching_coordinates_without_author_overlap_remain_flagged():
    metadata = {
        "doi": DQN_DOI,
        "title": "Human-level control through deep reinforcement learning",
        "authors": ["Volodymyr Mnih", "Koray Kavukcuoglu"],
        "year": 2015,
        "journal": "Nature",
        "volume": "518",
        "pages": "529-533",
    }
    citation = (
        "Vaswani, Shazeer. Attention Transformer Networks. Nature 518, "
        f"529-533 (2015). doi:{DQN_DOI}"
    )

    warning = IdentifierModule()._check_text_metadata_mismatch(citation, DQN_DOI, metadata)

    assert warning is not None
    assert warning["type"] == "text_metadata_mismatch"


def test_warning_reaches_cli_json_envelope(capsys):
    import argparse
    import json
    import os
    from onecite import cli

    namespace = argparse.Namespace(
        command="process",
        input="-",
        input_type="txt",
        template="journal_article_full",
        output_format="bibtex",
        output=None,
        quiet=True,
        as_json=True,
        as_ndjson=False,
        fail_on_unresolved=False,
    )
    text = f"Attention Is All You Need. Vaswani, A. et al. (2017). doi:{DQN_DOI}"
    with (
        patch.object(cli, "_read_input_content", return_value=text),
        patch.dict(os.environ, {"ONECITE_OFFLINE_FIXTURES": "1"}),
    ):
        code = cli.process_command(namespace)
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["succeeded"] == 1
    assert len(payload["warnings"]) == 1
    assert payload["warnings"][0]["type"] == "text_metadata_mismatch"
