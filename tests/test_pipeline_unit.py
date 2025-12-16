import builtins
import json
import types

import pytest
import requests
from unittest.mock import patch

from onecite.pipeline import EnricherModule, FormatterModule, IdentifierModule


class DummyResponse:
    def __init__(self, *, status_code=200, json_data=None, content=b"", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("HTTP error", response=self)


class ImmediateThread:
    def __init__(self, target=None, args=(), kwargs=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.daemon = False

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class NoopThread:
    def __init__(self, target=None, args=(), kwargs=None):
        self.daemon = False

    def start(self):
        return None


def test_identifier_extract_github_info():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/repos/owner/repo"):
            return DummyResponse(
                status_code=200,
                json_data={
                    "name": "repo",
                    "description": "desc",
                    "owner": {"login": "owner"},
                    "created_at": "2020-01-02T00:00:00Z",
                    "html_url": "https://github.com/owner/repo",
                    "language": "Python",
                    "stargazers_count": 123,
                },
            )
        if url.endswith("/repos/owner/repo/tags"):
            return DummyResponse(status_code=200, json_data=[{"name": "v1.2.3"}])
        return DummyResponse(status_code=404, json_data={})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        info = identifier._extract_github_info("https://github.com/owner/repo")

    assert info is not None
    assert info["source"] == "github"
    assert info["repo"] == "owner/repo"
    assert info["version"] == "1.2.3"


def test_identifier_extract_zenodo_info():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/api/records/12345"):
            return DummyResponse(
                status_code=200,
                json_data={
                    "metadata": {
                        "title": "Dataset",
                        "creators": [{"name": "A"}],
                        "publication_date": "2021-01-01",
                        "version": "1.0",
                        "resource_type": {"type": "dataset"},
                    }
                },
            )
        return DummyResponse(status_code=404, json_data={})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        info = identifier._extract_zenodo_info("10.5281/zenodo.12345")

    assert info is not None
    assert info["source"] == "zenodo"
    assert info["doi"] == "10.5281/zenodo.12345"
    assert info["title"] == "Dataset"
    assert info["authors"] == ["A"]


def test_identifier_extract_figshare_info():
    identifier = IdentifierModule()

    info = identifier._extract_zenodo_info("10.6084/m9.figshare.98765")
    assert info is not None
    assert info["source"] == "figshare"
    assert info["doi"] == "10.6084/m9.figshare.98765"


def test_identifier_extract_datacite_info_via_patterns():
    identifier = IdentifierModule()

    with patch.object(identifier, "_query_datacite", return_value={"source": "datacite", "doi": "10.5061/dryad.abc"}):
        info = identifier._extract_zenodo_info("10.5061/dryad.abc")

    assert info is not None
    assert info["source"] == "datacite"


def test_identifier_detect_thesis_openaire():
    identifier = IdentifierModule()

    with patch.object(
        identifier,
        "_search_openaire_for_thesis",
        return_value={"source": "openaire", "title": "Great Work", "authors": ["X"], "year": "2020", "school": "U", "url": "http://u", "type": "thesis"},
    ):
        thesis = identifier._detect_thesis("Smith, J. (2020). Great Work. PhD thesis. Stanford University.")

    assert thesis is not None
    assert thesis["is_thesis"] is True
    assert thesis["thesis_type"] == "phdthesis"
    assert thesis["authors"] == ["Smith, J."]


def test_identifier_search_pubmed_by_id():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/esummary.fcgi"):
            pmid = kwargs.get("params", {}).get("id")
            return DummyResponse(
                status_code=200,
                json_data={
                    "result": {
                        pmid: {
                            "title": "My Paper",
                            "articleids": [{"idtype": "doi", "value": "10.1234/abc"}],
                            "authors": [{"name": "Doe J"}],
                            "fulljournalname": "J",
                            "pubdate": "2020 Jan",
                            "volume": "1",
                            "issue": "2",
                            "pages": "3-4",
                        }
                    }
                },
            )
        return DummyResponse(status_code=404, json_data={})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        result = identifier._search_pubmed_by_id("1234567")

    assert result is not None
    assert result["source"] == "pubmed"
    assert result["doi"] == "10.1234/abc"
    assert result["year"] == "2020"


def test_identifier_search_pubmed_list():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/esearch.fcgi"):
            return DummyResponse(status_code=200, json_data={"esearchresult": {"idlist": ["1234567"]}})
        return DummyResponse(status_code=404, json_data={})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get), patch.object(
        identifier, "_search_pubmed_by_id", return_value={"source": "pubmed", "pmid": "1234567", "title": "T", "authors": ["A"]}
    ):
        results = identifier._search_pubmed("some query")

    assert len(results) == 1
    assert results[0]["pmid"] == "1234567"


def test_identifier_search_semantic_scholar_url_fallback():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        return DummyResponse(
            status_code=200,
            json_data={
                "data": [
                    {
                        "title": "T",
                        "authors": [{"name": "A"}],
                        "year": 2020,
                        "venue": "",
                        "journal": {"name": "J"},
                        "citationCount": 5,
                        "publicationDate": "2020-01-01",
                        "externalIds": None,
                        "paperId": "pid",
                        "url": None,
                    }
                ]
            },
        )

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        results = identifier._search_semantic_scholar("query")

    assert len(results) == 1
    assert results[0]["source"] == "semantic_scholar"
    assert results[0]["journal"] == "J"
    assert results[0]["url"].endswith("/pid")


def test_identifier_extract_arxiv_id_variants():
    identifier = IdentifierModule()

    assert identifier._extract_arxiv_id("arxiv:1706.03762") == "1706.03762"
    assert identifier._extract_arxiv_id("arXiv:1706.03762") == "1706.03762"
    assert identifier._extract_arxiv_id("1706.03762") == "1706.03762"
    assert identifier._extract_arxiv_id_from_url("https://arxiv.org/abs/1706.03762") == "1706.03762"


def test_identifier_extract_doi_from_url_meta_tag():
    identifier = IdentifierModule()

    html = """
    <html><head>
      <meta name="citation_doi" content="10.1234/xyz" />
    </head><body></body></html>
    """

    def fake_get(url, *args, **kwargs):
        return DummyResponse(status_code=200, content=html.encode("utf-8"))

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        doi = identifier._extract_doi_from_url("https://example.com/paper")

    assert doi == "10.1234/xyz"


def test_identifier_extract_doi_from_url_structured_data():
    identifier = IdentifierModule()

    html = """
    <html><head>
      <script type="application/ld+json">{"identifier": "10.2345/abc"}</script>
    </head><body></body></html>
    """

    def fake_get(url, *args, **kwargs):
        return DummyResponse(status_code=200, content=html.encode("utf-8"))

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        doi = identifier._extract_doi_from_url("https://example.com/paper")

    assert doi == "10.2345/abc"


def test_identifier_extract_doi_from_url_content():
    identifier = IdentifierModule()

    html = """
    <html><body><main>doi:10.3456/def</main></body></html>
    """

    def fake_get(url, *args, **kwargs):
        return DummyResponse(status_code=200, content=html.encode("utf-8"))

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        doi = identifier._extract_doi_from_url("https://example.com/paper")

    assert doi == "10.3456/def"


def test_identifier_extract_from_html_content_meta_and_fallbacks():
    identifier = IdentifierModule()

    html = """
    <html>
      <head>
        <meta name="citation_title" content="Title" />
        <meta name="citation_author" content="By Alice Smith" />
        <meta name="citation_author" content="Bob Jones" />
        <meta name="citation_publication_date" content="2019-01-01" />
      </head>
      <body><div class="byline">By Alice Smith</div></body>
    </html>
    """

    metadata = identifier._extract_from_html_content(html.encode("utf-8"))
    assert metadata is not None
    assert metadata["title"] == "Title"
    assert metadata["year"] == 2019
    assert "author" in metadata


def test_identifier_extract_from_pdf_content_importerror_branch():
    identifier = IdentifierModule()

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PyPDF2":
            raise ImportError("No PyPDF2")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        assert identifier._extract_from_pdf_content(b"%PDF") is None


def test_enricher_convert_search_metadata_dataset_and_key_and_strip_html():
    enricher = EnricherModule(use_google_scholar=False)

    converted = enricher._convert_search_metadata(
        {
            "source": "zenodo",
            "type": "dataset",
            "title": "T",
            "authors": ["A"],
            "year": 2020,
            "publisher": "Zenodo",
            "url": "https://example.com",
            "version": "1",
        }
    )
    assert converted is not None
    assert converted["howpublished"] == "Zenodo"
    assert converted["author"] == "A"

    key = enricher._generate_bibtex_key({"author": "Doe, John and Smith, Alice", "year": "2020", "title": "Deep Learning"})
    assert key == "Doe2020Deep"

    assert enricher._strip_html_tags("Human-level <i>control</i> &amp; learning") == "Human-level control & learning"


def test_enricher_complete_fields_google_scholar_disabled_returns_none():
    enricher = EnricherModule(use_google_scholar=False)

    assert enricher._fetch_missing_field("pages", ["google_scholar_scraper"], {"title": "T"}) is None


def test_formatter_escape_and_formats():
    formatter = FormatterModule()

    assert formatter._escape_latex_chars(r"K{\\\"u}nsch") == r"K{\\\"u}nsch"
    escaped = formatter._escape_latex_chars("Müller")
    assert "ü" not in escaped
    assert escaped.startswith("M{")
    assert escaped.endswith("}ller")

    completed_entry = {
        "id": 1,
        "doi": "10.1234/xyz",
        "status": "completed",
        "bib_key": "Doe2020Deep",
        "bib_data": {
            "ENTRYTYPE": "article",
            "ID": "Doe2020Deep",
            "author": "Doe, John and Smith, Alice",
            "title": "Deep Learning",
            "journal": "Nature",
            "year": 2020,
            "volume": "1",
            "number": "2",
            "pages": "3--4",
            "doi": "10.1234/xyz",
        },
    }

    result_bib = formatter.format([completed_entry], "bibtex")
    assert result_bib["report"]["succeeded"] == 1

    result_apa = formatter.format([completed_entry], "apa")
    assert result_apa["report"]["succeeded"] == 1

    result_mla = formatter.format([completed_entry], "mla")
    assert result_mla["report"]["succeeded"] == 1

    result_failed = formatter.format([{**completed_entry, "status": "enrichment_failed"}], "bibtex")
    assert result_failed["report"]["succeeded"] == 0
    assert len(result_failed["report"]["failed_entries"]) == 1


def test_identifier_resolve_doi_via_crossref_title_success():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        return DummyResponse(
            status_code=200,
            json_data={
                "message": {
                    "items": [
                        {
                            "title": ["Deep Learning"],
                            "DOI": "10.1000/abc",
                            "author": [{"given": "Ian", "family": "Goodfellow"}],
                            "container-title": ["Nature"],
                            "published-print": {"date-parts": [[2016]]},
                            "is-referenced-by-count": 10,
                        },
                        {"title": ["Other"], "DOI": "10.1000/def"},
                    ]
                }
            },
        )

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        resolved = identifier._resolve_doi_via_crossref_title("Deep Learning", "Deep Learning 2016")

    assert resolved is not None
    assert resolved["doi"] == "10.1000/abc"
    assert resolved["source"] == "crossref"


def test_identifier_search_crossref_dedup_and_event_and_book_fields():
    identifier = IdentifierModule()

    call_count = {"n": 0}

    def fake_get(url, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return DummyResponse(
                status_code=200,
                json_data={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1111/aaa",
                                "title": ["Paper A"],
                                "type": "proceedings-article",
                                "author": [{"given": "A", "family": "B"}],
                                "event": {"name": ["NeurIPS"]},
                                "issued": {"date-parts": [[2020]]},
                                "is-referenced-by-count": 5,
                                "publisher": "P",
                            }
                        ]
                    }
                },
            )

        if call_count["n"] == 2:
            return DummyResponse(
                status_code=200,
                json_data={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1111/aaa",
                                "title": ["Paper A"],
                                "type": "proceedings-article",
                            },
                            {
                                "DOI": "10.2222/book",
                                "title": ["A Great Book"],
                                "type": "book",
                                "ISBN": ["9780000000001"],
                                "publisher": "Wiley",
                                "author": [{"given": "C", "family": "D"}],
                                "published-online": {"date-parts": [[2018]]},
                            },
                        ]
                    }
                },
            )

        return DummyResponse(status_code=200, json_data={"message": {"items": []}})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        results = identifier._search_crossref("query", limit=10)

    assert len(results) == 2
    assert {r["doi"] for r in results} == {"10.1111/aaa", "10.2222/book"}
    conf = next(r for r in results if r["doi"] == "10.1111/aaa")
    assert conf["journal"] == "NeurIPS"
    book = next(r for r in results if r["doi"] == "10.2222/book")
    assert book.get("is_book") is True
    assert book.get("isbn") == "9780000000001"


def test_identifier_search_google_books_success_and_edition_and_isbn_extraction():
    identifier = IdentifierModule()

    captured = {"params": None}

    def fake_get(url, *args, **kwargs):
        captured["params"] = kwargs.get("params")
        return DummyResponse(
            status_code=200,
            json_data={
                "items": [
                    {
                        "volumeInfo": {
                            "title": "Deep Learning",
                            "subtitle": "2nd edition",
                            "authors": ["John Doe"],
                            "publisher": "Cambridge University Press",
                            "publishedDate": "2020-01-01",
                            "industryIdentifiers": [
                                {"type": "ISBN_13", "identifier": "9780000000001"}
                            ],
                            "pageCount": 500,
                            "infoLink": "https://books.example/book",
                        }
                    }
                ]
            },
        )

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        results = identifier._search_google_books("Doe, J. (2020). Deep Learning (2nd ed.). Cambridge University Press.")

    assert len(results) == 1
    assert results[0]["is_book"] is True
    assert results[0]["isbn"] == "9780000000001"
    assert results[0]["edition"] == "2"
    assert captured["params"] is not None
    assert "q" in captured["params"]


def test_identifier_search_google_scholar_success_threaded_worker_is_fast():
    identifier = IdentifierModule(use_google_scholar=True)

    pubs = [
        {
            "bib": {
                "title": "NeurIPS Paper",
                "author": "Doe, John and Smith, Alice",
                "pub_year": "2019",
                "venue": "NeurIPS",
            },
            "num_citations": 12,
            "pub_url": "https://doi.org/10.9999/xyz",
            "eprint": "arXiv:1706.03762",
        }
    ]

    with patch("threading.Thread", ImmediateThread), patch("time.sleep", lambda *_args, **_kwargs: None), patch(
        "time.time", lambda: 1000.0
    ), patch("onecite.pipeline.scholarly.search_pubs", return_value=pubs):
        results = identifier._search_google_scholar("neurips paper", limit=1)

    assert len(results) == 1
    assert results[0]["source"] == "google_scholar"
    assert results[0]["doi"] == "10.9999/xyz"
    assert results[0]["arxiv_id"] == "1706.03762"
    assert results[0]["type"] == "conference"


def test_identifier_fuzzy_search_well_known_paper_shortcut():
    identifier = IdentifierModule()

    raw_entry = {
        "id": 1,
        "raw_text": "Attention is all you need",
        "query_string": "Attention is all you need",
    }

    result = identifier._fuzzy_search(raw_entry, lambda _c: -1)
    assert result["status"] == "identified"
    assert result["arxiv_id"] == "1706.03762"


def test_identifier_fuzzy_search_pmid_shortcut():
    identifier = IdentifierModule()

    raw_entry = {
        "id": 2,
        "raw_text": "PMID:12345678",
        "query_string": "PMID:12345678",
    }

    with patch.object(
        identifier,
        "_search_pubmed_by_id",
        return_value={"source": "pubmed", "doi": "10.1234/pmid", "url": "https://example.com"},
    ):
        result = identifier._fuzzy_search(raw_entry, lambda _c: -1)

    assert result["status"] == "identified"
    assert result["doi"] == "10.1234/pmid"


def test_identifier_fuzzy_search_book_route_prefers_primary_google_books():
    identifier = IdentifierModule()

    raw_entry = {
        "id": 3,
        "raw_text": "Doe, J. (2020). Deep Learning (2nd ed.). Wiley.",
        "query_string": "Doe, J. (2020). Deep Learning (2nd ed.). Wiley.",
    }

    google_books_candidate = {
        "source": "google_books",
        "is_book": True,
        "type": "book",
        "title": "Deep Learning",
        "authors": ["John Doe"],
        "publisher": "Wiley",
        "year": 2020,
        "url": "https://books.example/book",
        "citations": 0,
        "is_primary_google_books_match": True,
    }
    crossref_candidate = {
        "source": "crossref",
        "doi": "10.0000/low",
        "title": "Unrelated",
        "authors": ["Someone"],
        "year": 2020,
        "journal": "",
        "citations": 0,
        "type": "book",
        "publisher": "Wiley",
    }

    with patch.object(identifier, "_search_google_books", return_value=[google_books_candidate]), patch.object(
        identifier, "_search_crossref", return_value=[crossref_candidate]
    ):
        result = identifier._fuzzy_search(raw_entry, lambda _c: -1)

    assert result["status"] == "identified"
    assert result["metadata"]["source"] == "google_books"


def test_identifier_fuzzy_search_interactive_branch_selects_user_choice():
    identifier = IdentifierModule()

    raw_entry = {
        "id": 4,
        "raw_text": "Some query",
        "query_string": "Some query",
    }

    scored = [
        {"source": "crossref", "doi": "10.1/a", "title": "A", "match_score": 75, "url": "https://doi.org/10.1/a"},
        {"source": "crossref", "doi": "10.1/b", "title": "B", "match_score": 74, "url": "https://doi.org/10.1/b"},
    ]

    with patch.object(identifier, "_search_crossref", return_value=[{"doi": "10.1/a"}]), patch.object(
        identifier, "_score_candidates", return_value=scored
    ):
        result = identifier._fuzzy_search(raw_entry, lambda c: 1)

    assert result["status"] == "identified"
    assert result["doi"] == "10.1/b"


def test_identifier_search_base_for_thesis_success():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        return DummyResponse(
            status_code=200,
            json_data={
                "response": {
                    "docs": [
                        {
                            "dctitle": ["Thesis Title"],
                            "dcauthor": ["Doe, John"],
                            "dcyear": ["2020"],
                            "dccreator": ["Test University"],
                            "dclink": ["https://example.com/thesis"],
                        }
                    ]
                }
            },
        )

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        result = identifier._search_base_for_thesis("Some Thesis PhD dissertation", year=2020)

    assert result is not None
    assert result["source"] == "base_search"
    assert result["type"] == "thesis"
    assert result["title"] == "Thesis Title"


def test_identifier_search_openaire_for_thesis_success():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        return DummyResponse(
            status_code=200,
            json_data={
                "response": {
                    "results": {
                        "result": [
                            {
                                "metadata": {
                                    "oaf:entity": {
                                        "oaf:result": {
                                            "title": {"$": "external providerRE Thesis"},
                                            "creator": [{"$": "Doe, John"}],
                                            "dateofacceptance": {"$": "2021-01-01"},
                                            "publisher": {"$": "external providerRE University"},
                                            "children": {
                                                "instance": [
                                                    {
                                                        "webresource": {
                                                            "url": {"$": "https://example.com/openaire"}
                                                        }
                                                    }
                                                ]
                                            },
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            },
        )

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        result = identifier._search_openaire_for_thesis("external providerRE Thesis", year=2021)

    assert result is not None
    assert result["source"] == "openaire"
    assert result["title"] == "external providerRE Thesis"
    assert result["school"] == "external providerRE University"
    assert result["url"] == "https://example.com/openaire"


def test_identifier_detect_thesis_manual_fallback_when_no_apis():
    identifier = IdentifierModule()

    with patch.object(identifier, "_search_openaire_for_thesis", return_value=None), patch.object(
        identifier, "_search_base_for_thesis", return_value=None
    ):
        result = identifier._detect_thesis("Doe, J. (2020). Great Thesis. PhD thesis. Test University.")

    assert result is not None
    assert result["source"] == "manual"
    assert result["is_thesis"] is True
    assert result["thesis_type"] == "phdthesis"


def test_identifier_extract_metadata_from_url_html_path():
    identifier = IdentifierModule()

    html = """
    <html>
      <head><title>My Very Long Paper Title - PDF Download</title></head>
      <body>
        <div class="authors">By Alice Smith, Bob Jones</div>
        <p>Published 2021.</p>
      </body>
    </html>
    """

    def fake_get(url, *args, **kwargs):
        return DummyResponse(status_code=200, content=html.encode("utf-8"), headers={"content-type": "text/html"})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        meta = identifier._extract_metadata_from_url("https://example.com/page")

    assert meta is not None
    assert meta["title"] == "My Very Long Paper Title"
    assert meta["year"] == 2021
    assert "Alice Smith" in meta["author"]


def test_identifier_extract_metadata_from_url_pdf_path_calls_pdf_extractor():
    identifier = IdentifierModule()

    def fake_get(url, *args, **kwargs):
        return DummyResponse(status_code=200, content=b"%PDF", headers={"content-type": "application/pdf"})

    with patch("onecite.pipeline.requests.get", side_effect=fake_get), patch.object(
        identifier, "_extract_from_pdf_content", return_value={"title": "T"}
    ) as mocked_pdf:
        meta = identifier._extract_metadata_from_url("https://example.com/file.pdf")

    assert meta == {"title": "T"}
    assert mocked_pdf.called


def test_identifier_extract_from_pdf_content_success_branch_with_fake_pypdf2():
    identifier = IdentifierModule()

    class FakePage:
        def extract_text(self):
            return "Some content 2019\n"

    class FakePdfReader:
        def __init__(self, _file):
            self.metadata = {"/Title": "Meta Title", "/Author": "John Doe"}
            self.pages = [FakePage()]

    fake_pypdf2 = types.SimpleNamespace(PdfReader=FakePdfReader)

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PyPDF2":
            return fake_pypdf2
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        meta = identifier._extract_from_pdf_content(b"%PDF")

    assert meta is not None
    assert meta["title"] == "Meta Title"
    assert meta["author"] == "John Doe"
    assert meta["year"] == 2019


def test_identifier_search_google_scholar_captcha_error_retries_and_returns_empty():
    identifier = IdentifierModule(use_google_scholar=True)

    with patch("threading.Thread", ImmediateThread), patch("time.sleep", lambda *_args, **_kwargs: None), patch(
        "time.time", lambda: 1000.0
    ), patch("onecite.pipeline.scholarly.search_pubs", side_effect=Exception("captcha blocked")):
        results = identifier._search_google_scholar("q", limit=1)

    assert results == []


def test_enricher_fetch_missing_field_google_scholar_success_threaded():
    enricher = EnricherModule(use_google_scholar=True)

    def fake_search_pubs(_query):
        yield {"pages": "123--130"}

    base_record = {"title": "T", "author": "Doe, John", "year": "2020"}

    with patch("threading.Thread", ImmediateThread), patch("time.sleep", lambda *_args, **_kwargs: None), patch(
        "time.time", lambda: 1000.0
    ), patch("onecite.pipeline.scholarly.search_pubs", side_effect=fake_search_pubs):
        value = enricher._fetch_missing_field("pages", ["google_scholar_scraper"], base_record)

    assert value == "123--130"


def test_enricher_fetch_from_google_scholar_timeout_returns_none():
    enricher = EnricherModule(use_google_scholar=True)

    base_record = {"title": "T"}

    with patch("threading.Thread", NoopThread), patch("time.sleep", lambda *_args, **_kwargs: None), patch(
        "time.time", lambda: 1000.0
    ):
        value = enricher._fetch_from_google_scholar("pages", base_record)

    assert value is None


def test_enricher_fetch_from_google_scholar_worker_error_returns_none():
    enricher = EnricherModule(use_google_scholar=True)

    base_record = {"title": "T"}

    with patch("threading.Thread", ImmediateThread), patch("time.sleep", lambda *_args, **_kwargs: None), patch(
        "time.time", lambda: 1000.0
    ), patch("onecite.pipeline.scholarly.search_pubs", side_effect=RuntimeError("boom")):
        value = enricher._fetch_from_google_scholar("pages", base_record)

    assert value is None


def test_identifier_search_google_scholar_timeout_path_returns_empty():
    identifier = IdentifierModule(use_google_scholar=True)

    with patch("threading.Thread", NoopThread), patch("time.sleep", lambda *_args, **_kwargs: None), patch(
        "time.time", lambda: 1000.0
    ):
        results = identifier._search_google_scholar("q", limit=1)

    assert results == []
