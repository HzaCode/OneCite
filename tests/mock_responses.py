"""
Hand-crafted mock responses for the external APIs we hit at runtime.

Why only Crossref + arXiv?
  These two cover the two most common lookup paths (DOI-based and
  arXiv-based).  Semantic Scholar / PubMed / Google Books paths are
  exercised through unit-level mocks in ``test_pipeline_unit.py``
  instead, because their real API shapes change too often to maintain
  a single canned response here.
"""

# -- Crossref -----------------------------------------------------------------
# Corresponds to DOI 10.1038/nature14539 (Mnih et al., 2015 – DQN paper).
MOCK_CROSSREF_RESPONSE = {
    "status": "ok",
    "message-type": "work",
    "message": {
        "DOI": "10.1038/nature14539",
        "type": "journal-article",
        "title": ["Human-level control through deep reinforcement learning"],
        "author": [
            {"given": "Volodymyr", "family": "Mnih", "sequence": "first"},
            {"given": "Koray", "family": "Kavukcuoglu", "sequence": "additional"},
            {"given": "David", "family": "Silver", "sequence": "additional"},
        ],
        "container-title": ["Nature"],
        "published-print": {"date-parts": [[2015, 2, 26]]},
        "volume": "518",
        "issue": "7540",
        "page": "529-533",
        "publisher": "Springer Nature",
        "ISSN": ["0028-0836", "1476-4687"],
    },
}

# -- arXiv --------------------------------------------------------------------
# 1706.03762 = "Attention Is All You Need"
MOCK_ARXIV_RESPONSE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <updated>2017-12-06T00:00:00Z</updated>
    <published>2017-06-12T00:00:00Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <author><name>Niki Parmar</name></author>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.5555/3295222.3295349</arxiv:doi>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">15 pages, 5 figures</arxiv:comment>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom"
        term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""

# -- Crossref title search (used by _resolve_doi_via_crossref_title) ----------
MOCK_CROSSREF_SEARCH_RESPONSE = {
    "status": "ok",
    "message-type": "work-list",
    "message": {
        "items": [
            {
                "DOI": "10.5555/3295222.3295349",
                "title": ["Attention Is All You Need"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "container-title": ["Advances in Neural Information Processing Systems"],
                "type": "proceedings-article",
                "issued": {"date-parts": [[2017]]},
                "is-referenced-by-count": 90000,
            }
        ],
    },
}

# -- Semantic Scholar (partial, for the arXiv paper) --------------------------
MOCK_S2_RESPONSE = {
    "data": [
        {
            "title": "Attention Is All You Need",
            "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
            "year": 2017,
            "venue": "NeurIPS",
            "journal": {"name": "Advances in Neural Information Processing Systems"},
            "citationCount": 90000,
            "publicationDate": "2017-06-12",
            "externalIds": {"DOI": "10.5555/3295222.3295349", "ArXiv": "1706.03762"},
            "paperId": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
            "url": "https://www.semanticscholar.org/paper/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        }
    ]
}


# -- Pre-rendered BibTeX strings (for tests that check final output) ----------

MOCK_BIBTEX_DOI = """\
@article{Mnih2015,
  author = {Mnih, Volodymyr and Kavukcuoglu, Koray and Silver, David},
  title = {Human-level control through deep reinforcement learning},
  journal = {Nature},
  year = {2015},
  volume = {518},
  number = {7540},
  pages = {529--533},
  doi = {10.1038/nature14539},
  publisher = {Springer Nature}
}"""

MOCK_BIBTEX_ARXIV = """\
@article{Vaswani2017,
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  title = {Attention Is All You Need},
  journal = {arXiv preprint arXiv:1706.03762},
  year = {2017},
  url = {https://arxiv.org/abs/1706.03762}
}"""

MOCK_BIBTEX_CONFERENCE = """\
@inproceedings{Vaswani2017,
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  title = {Attention Is All You Need},
  booktitle = {Advances in Neural Information Processing Systems},
  year = {2017},
  pages = {5998--6008}
}"""


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, json_data=None, text="", status_code=200):
        self.json_data = json_data
        self.text = text
        self.content = text.encode("utf-8") if text else b""
        self.status_code = status_code
        self.ok = status_code == 200

    def json(self):
        if self.json_data is None:
            raise ValueError("No JSON data")
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(f"HTTP {self.status_code}", response=self)


def mock_requests_get(url, *args, **kwargs):
    """Drop-in replacement for ``requests.get`` used by the fixtures.

    Only the URLs that our integration / template / output-format tests
    actually trigger are routed here.  Everything else falls through to a
    404 so that new code-paths fail loudly instead of silently passing.
    """
    # Crossref: single-work lookup by DOI
    if "api.crossref.org" in url and "10.1038/nature14539" in url:
        return MockResponse(json_data=MOCK_CROSSREF_RESPONSE)

    # Crossref: title search (fuzzy-search path)
    if "api.crossref.org" in url and "query" in str(kwargs.get("params", "")):
        return MockResponse(json_data=MOCK_CROSSREF_SEARCH_RESPONSE)

    # arXiv
    if "export.arxiv.org" in url and "1706.03762" in url:
        return MockResponse(text=MOCK_ARXIV_RESPONSE)

    # Semantic Scholar
    if "api.semanticscholar.org" in url:
        return MockResponse(json_data=MOCK_S2_RESPONSE)

    # Anything we haven't explicitly mocked → 404
    return MockResponse(json_data={}, status_code=404)


def get_mock_bibtex_output(input_text):
    """Quick lookup for expected BibTeX output in snapshot-style tests."""
    low = input_text.lower()
    if "10.1038/nature14539" in low:
        return MOCK_BIBTEX_DOI
    if "1706.03762" in low or "arxiv" in low:
        return MOCK_BIBTEX_ARXIV
    if "attention" in low and "need" in low:
        return MOCK_BIBTEX_CONFERENCE
    return (
        "@article{Unknown,\n"
        "  author = {Unknown Author},\n"
        "  title = {Unknown Title},\n"
        "  journal = {Unknown Journal},\n"
        "  year = {2020}\n"
        "}"
    )
