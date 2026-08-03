"""Regression tests for real citation-string retrieval and reranking."""

from unittest.mock import patch

from onecite.pipeline import IdentifierModule


class DummyResponse:
    status_code = 200

    def __init__(self, items):
        self._items = items

    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"items": self._items}}


def _crossref_item(doi, title, score=100.0):
    return {
        "DOI": doi,
        "title": [title],
        "author": [{"given": "A", "family": "Author"}],
        "issued": {"date-parts": [[1993]]},
        "type": "journal-article",
        "score": score,
    }


def test_crossref_uses_bibliographic_query_first_and_preserves_rank():
    identifier = IdentifierModule()
    captured = {}
    response = DummyResponse(
        [
            _crossref_item("10.1/correct", "Correct work", 55.0),
            _crossref_item("10.1/other", "Other work", 50.0),
        ]
    )

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return response

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        results = identifier._search_crossref("Author. Correct work. Journal 1993", limit=2)

    assert captured["params"]["query.bibliographic"] == "Author. Correct work. Journal 1993"
    assert "query" not in captured["params"]
    assert "query.title" not in captured["params"]
    assert captured["headers"]["User-Agent"].startswith("OneCite")
    assert [item["_source_rank"] for item in results] == [1, 2]
    assert [item["_source_score"] for item in results] == [55.0, 50.0]


def test_title_embedded_in_full_citation_outweighs_year_prefix_author_text():
    identifier = IdentifierModule()
    query = (
        "LaBerge D, Buchsbaum MS (1990) Positron emission tomographic measurements "
        "of pulvinar activity during an attention task. J Neurosci 10:613-619"
    )
    candidates = [
        {
            "source": "crossref",
            "doi": "10.1/lookalike",
            "title": "Thalamic and Cortical Mechanisms of Attention",
            "authors": ["D LaBerge"],
            "year": 1990,
            "_source_rank": 2,
        },
        {
            "source": "crossref",
            "doi": "10.1/correct",
            "title": (
                "Positron emission tomographic measurements of pulvinar activity "
                "during an attention task"
            ),
            "authors": ["D LaBerge", "M S Buchsbaum"],
            "year": 1990,
            "_source_rank": 1,
        },
    ]

    ranked = identifier._score_candidates(candidates, query)

    assert ranked[0]["doi"] == "10.1/correct"
    assert ranked[0]["score_breakdown"]["title"] >= 90


def test_crossref_rank_breaks_sparse_citation_near_tie():
    identifier = IdentifierModule()
    query = "B. Derrida, M.R. Evans, V. Hakim and V. Pasquier J. Phys. A 26 1493 (1993)."
    candidates = [
        {
            "source": "crossref",
            "doi": "10.1/wrong",
            "title": "The free energy in a Derrida recursive model",
            "authors": ["B Derrida"],
            "year": 1993,
            "_source_rank": 2,
        },
        {
            "source": "crossref",
            "doi": "10.1/correct",
            "title": "Exact solution of a one-dimensional asymmetric exclusion model",
            "authors": ["B Derrida", "M R Evans", "V Hakim", "V Pasquier"],
            "year": 1993,
            "_source_rank": 1,
        },
    ]

    ranked = identifier._score_candidates(candidates, query)

    assert ranked[0]["doi"] == "10.1/correct"
