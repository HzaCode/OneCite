"""Regression tests for real-world citation-cleanup risks.

These tests exercise behavior that matters when OneCite is used on an
existing manuscript bibliography rather than on isolated demo inputs.
"""

from unittest.mock import patch

from onecite.pipeline import EnricherModule, IdentifierModule
from tests.test_pipeline_unit import DummyResponse


def test_bibtex_input_preserves_existing_citation_key_when_enriched():
    enricher = EnricherModule(use_google_scholar=False)
    identified = {
        "id": 0,
        "status": "identified",
        "doi": "10.1234/example",
        "metadata": {},
    }
    raw = {
        "id": 0,
        "raw_text": "@article{localKey2026,...}",
        "doi": "10.1234/example",
        "original_entry": {
            "ENTRYTYPE": "article",
            "ID": "localKey2026",
            "title": "Local Manuscript Citation",
            "author": "Doe, Jane",
            "journal": "Local Journal",
            "year": "2026",
            "doi": "10.1234/example",
        },
    }
    crossref_record = {
        "title": "Local Manuscript Citation",
        "author": "Doe, Jane",
        "journal": "Local Journal",
        "year": "2026",
        "doi": "10.1234/example",
    }

    with patch.object(enricher, "_get_crossref_metadata", return_value=crossref_record):
        result = enricher._enrich_single_entry(
            identified,
            {"entry_type": "@article", "fields": []},
            raw,
        )

    assert result["status"] == "completed"
    assert result["bib_key"] == "localKey2026"
    assert result["bib_data"]["ID"] == "localKey2026"


def test_doi_backed_bibtex_conflict_does_not_keep_wrong_core_fields():
    enricher = EnricherModule(use_google_scholar=False)
    identified = {
        "id": 0,
        "status": "identified",
        "doi": "10.1038/nature14539",
        "metadata": {},
    }
    raw = {
        "id": 0,
        "raw_text": "@article{badkey,...}",
        "doi": "10.1038/nature14539",
        "original_entry": {
            "ENTRYTYPE": "article",
            "ID": "badkey",
            "title": "Totally Wrong Local Title",
            "author": "Someone, Alice",
            "journal": "Imaginary Journal",
            "year": "1900",
            "doi": "10.1038/nature14539",
        },
    }
    canonical_record = {
        "title": "Deep learning",
        "author": "LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey",
        "journal": "Nature",
        "year": "2015",
        "volume": "521",
        "number": "7553",
        "pages": "436--444",
        "doi": "10.1038/nature14539",
    }

    with patch.object(enricher, "_get_crossref_metadata", return_value=canonical_record):
        result = enricher._enrich_single_entry(
            identified,
            {"entry_type": "@article", "fields": []},
            raw,
        )

    bib_data = result["bib_data"]
    assert bib_data["title"] == canonical_record["title"]
    assert bib_data["author"] == canonical_record["author"]
    assert bib_data["journal"] == canonical_record["journal"]
    assert bib_data["year"] == canonical_record["year"]


def test_verify_doi_crossref_request_uses_polite_headers_and_mailto():
    identifier = IdentifierModule()
    captured = {}

    def fake_get(url, *args, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers", {})
        captured["params"] = kwargs.get("params", {})
        return DummyResponse(
            json_data={
                "message": {
                    "DOI": "10.1234/example",
                    "title": ["Example Paper"],
                    "author": [{"given": "Jane", "family": "Doe"}],
                    "published-print": {"date-parts": [[2026]]},
                }
            }
        )

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        metadata, failure = identifier._verify_doi_and_get_metadata("10.1234/example")

    assert failure is None
    assert metadata["doi"] == "10.1234/example"
    assert "api.crossref.org/works/10.1234/example" in captured["url"]
    assert "OneCite" in captured["headers"].get("User-Agent", "")
    assert captured["params"].get("mailto")


def test_plain_text_query_is_unresolved_in_process_identifier_path():
    identifier = IdentifierModule()
    raw_entry = {
        "id": 0,
        "raw_text": "Attention is all you need, Vaswani et al., NIPS 2017",
        "query_string": "Attention is all you need, Vaswani et al., NIPS 2017",
    }

    result = identifier._identify_single_entry(raw_entry, interactive_callback=lambda _c: 0)

    assert result["status"] == "identification_failed"
    assert result["doi"] is None


def test_plain_text_query_can_return_suggestions_without_identifying():
    identifier = IdentifierModule()
    raw_entry = {
        "id": 0,
        "raw_text": "Attention is all you need, Vaswani et al., NIPS 2017",
        "query_string": "Attention is all you need, Vaswani et al., NIPS 2017",
    }
    candidate = {
        "source": "crossref",
        "doi": "10.5555/3295222.3295349",
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani"],
        "year": "2017",
        "journal": "Advances in Neural Information Processing Systems",
        "match_score": 92,
        "_weights": {"title": 1.0},
    }

    with (
        patch.object(identifier, "_search_crossref", return_value=[candidate]),
        patch.object(identifier, "_search_semantic_scholar", return_value=[]),
        patch.object(identifier, "_search_arxiv_candidates", return_value=[]),
        patch.object(identifier, "_search_google_books", return_value=[]),
        patch.object(identifier, "_score_candidates", return_value=[candidate]),
    ):
        suggestion = identifier.suggest(raw_entry, limit=3)

    assert suggestion["id"] == 0
    assert suggestion["status"] == "candidates_found"
    assert suggestion["query_string"] == raw_entry["query_string"]
    assert suggestion["candidates"][0]["doi"] == candidate["doi"]
    assert "_weights" not in suggestion["candidates"][0]
