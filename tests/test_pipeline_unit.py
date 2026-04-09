"""
Unit tests for the three pipeline modules (Identifier → Enricher → Formatter).

Every test here mocks HTTP at the ``requests.get`` level so we never
touch real APIs.  The helper classes at the top (DummyResponse, ImmediateThread,
NoopThread) keep the individual test bodies short and readable.

Note: synthetic DOIs like 10.1234/xyz are used intentionally – they don't
exist on Crossref, which makes it obvious when a mock is missing.
"""
import builtins
import io
import json
import types

import pytest
import requests
from unittest.mock import patch, MagicMock

from onecite.pipeline import EnricherModule, FormatterModule, IdentifierModule
import onecite.pipeline as _pipeline_mod


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class DummyResponse:
    """Minimal ``requests.Response`` stand-in."""

    def __init__(self, *, status_code=200, json_data=None, content=b"", headers=None):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.headers = headers or {}
        self.raw = io.BytesIO(content)

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("HTTP error", response=self)


class ImmediateThread:
    """Runs the target synchronously in ``start()`` – no real threading."""
    def __init__(self, target=None, args=(), kwargs=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.daemon = False

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class NoopThread:
    """start() does nothing → simulates a thread that never finishes."""
    def __init__(self, target=None, args=(), kwargs=None):
        self.daemon = False

    def start(self):
        pass


# ===================================================================
# IdentifierModule
# ===================================================================

class TestIdentifierGitHub:

    def test_extracts_repo_info(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            if url.endswith("/repos/owner/repo"):
                return DummyResponse(json_data={
                    "name": "repo", "description": "desc",
                    "owner": {"login": "owner"},
                    "created_at": "2020-01-02T00:00:00Z",
                    "html_url": "https://github.com/owner/repo",
                    "language": "Python", "stargazers_count": 123,
                })
            if url.endswith("/repos/owner/repo/tags"):
                return DummyResponse(json_data=[{"name": "v1.2.3"}])
            return DummyResponse(status_code=404, json_data={})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            info = ident._extract_github_info("https://github.com/owner/repo")

        assert info["source"] == "github"
        assert info["repo"] == "owner/repo"
        assert info["version"] == "1.2.3"  # "v" prefix stripped


class TestIdentifierZenodo:

    def test_extracts_zenodo_metadata(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            if "/api/records/12345" in url:
                return DummyResponse(json_data={
                    "metadata": {
                        "title": "Dataset", "creators": [{"name": "A"}],
                        "publication_date": "2021-01-01", "version": "1.0",
                        "resource_type": {"type": "dataset"},
                    }
                })
            return DummyResponse(status_code=404, json_data={})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            info = ident._extract_zenodo_info("10.5281/zenodo.12345")

        assert info["source"] == "zenodo"
        assert info["doi"] == "10.5281/zenodo.12345"
        assert info["title"] == "Dataset"
        assert info["authors"] == ["A"]

    def test_figshare_doi_recognised(self):
        ident = IdentifierModule()
        info = ident._extract_zenodo_info("10.6084/m9.figshare.98765")
        assert info["source"] == "figshare"

    def test_datacite_fallback(self):
        ident = IdentifierModule()
        with patch.object(ident, "_query_datacite",
                          return_value={"source": "datacite", "doi": "10.5061/dryad.abc"}):
            info = ident._extract_zenodo_info("10.5061/dryad.abc")
        assert info["source"] == "datacite"


class TestIdentifierPubMed:

    def test_lookup_by_id(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            if url.endswith("/esummary.fcgi"):
                pmid = kw.get("params", {}).get("id")
                return DummyResponse(json_data={
                    "result": {pmid: {
                        "title": "My Paper",
                        "articleids": [{"idtype": "doi", "value": "10.1234/abc"}],
                        "authors": [{"name": "Doe J"}],
                        "fulljournalname": "J",
                        "pubdate": "2020 Jan",
                        "volume": "1", "issue": "2", "pages": "3-4",
                    }}
                })
            return DummyResponse(status_code=404, json_data={})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            r = ident._search_pubmed_by_id("1234567")

        assert r["source"] == "pubmed"
        assert r["doi"] == "10.1234/abc"
        assert r["year"] == "2020"

    def test_search_returns_list(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            if url.endswith("/esearch.fcgi"):
                return DummyResponse(json_data={"esearchresult": {"idlist": ["1234567"]}})
            return DummyResponse(status_code=404, json_data={})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get), \
             patch.object(ident, "_search_pubmed_by_id",
                          return_value={"source": "pubmed", "pmid": "1234567",
                                        "title": "T", "authors": ["A"]}):
            results = ident._search_pubmed("some query")

        assert len(results) == 1
        assert results[0]["pmid"] == "1234567"


class TestIdentifierSemanticScholar:

    def test_url_fallback(self):
        """When the paper has no explicit URL, we build one from paperId."""
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            return DummyResponse(json_data={"data": [{
                "title": "T", "authors": [{"name": "A"}], "year": 2020,
                "venue": "", "journal": {"name": "J"}, "citationCount": 5,
                "publicationDate": "2020-01-01", "externalIds": None,
                "paperId": "pid", "url": None,
            }]})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            results = ident._search_semantic_scholar("query")

        assert len(results) == 1
        assert results[0]["source"] == "semantic_scholar"
        assert results[0]["journal"] == "J"
        assert results[0]["url"].endswith("/pid")


class TestIdentifierArxiv:

    def test_id_extraction_variants(self):
        ident = IdentifierModule()
        assert ident._extract_arxiv_id("arxiv:1706.03762") == "1706.03762"
        assert ident._extract_arxiv_id("arXiv:1706.03762") == "1706.03762"
        assert ident._extract_arxiv_id("1706.03762") == "1706.03762"
        assert ident._extract_arxiv_id_from_url(
            "https://arxiv.org/abs/1706.03762") == "1706.03762"


class TestIdentifierDOIExtraction:

    def test_from_meta_tag(self):
        ident = IdentifierModule()
        html = '<html><head><meta name="citation_doi" content="10.1234/xyz" /></head></html>'

        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(content=html.encode())):
            assert ident._extract_doi_from_url("https://example.com/paper") == "10.1234/xyz"

    def test_from_structured_data(self):
        ident = IdentifierModule()
        html = ('<html><head><script type="application/ld+json">'
                '{"identifier": "10.2345/abc"}</script></head></html>')

        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(content=html.encode())):
            assert ident._extract_doi_from_url("https://example.com/paper") == "10.2345/abc"

    def test_from_body_text(self):
        ident = IdentifierModule()
        html = '<html><body><main>doi:10.3456/def</main></body></html>'

        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(content=html.encode())):
            assert ident._extract_doi_from_url("https://example.com/paper") == "10.3456/def"


class TestIdentifierHTMLMetadata:

    def test_citation_meta_tags(self):
        ident = IdentifierModule()
        html = """
        <html><head>
          <meta name="citation_title" content="Title" />
          <meta name="citation_author" content="By Alice Smith" />
          <meta name="citation_author" content="Bob Jones" />
          <meta name="citation_publication_date" content="2019-01-01" />
        </head><body><div class="byline">By Alice Smith</div></body></html>
        """
        meta = ident._extract_from_html_content(html.encode("utf-8"))
        assert meta["title"] == "Title"
        assert meta["year"] == 2019
        assert "author" in meta


class TestIdentifierPDF:

    def test_importerror_branch(self):
        """If PyPDF2 isn't installed we should return None, not crash."""
        ident = IdentifierModule()
        real_import = builtins.__import__

        def _no_pypdf2(name, *a, **kw):
            if name == "PyPDF2":
                raise ImportError
            return real_import(name, *a, **kw)

        with patch("builtins.__import__", side_effect=_no_pypdf2):
            assert ident._extract_from_pdf_content(b"%PDF") is None

    def test_success_with_fake_reader(self):
        ident = IdentifierModule()

        class FakePage:
            def extract_text(self):
                return "Some content 2019\n"

        class FakeReader:
            def __init__(self, _):
                self.metadata = {"/Title": "Meta Title", "/Author": "John Doe"}
                self.pages = [FakePage()]

        fake_mod = types.SimpleNamespace(PdfReader=FakeReader)
        real_import = builtins.__import__

        def _inject(name, *a, **kw):
            return fake_mod if name == "PyPDF2" else real_import(name, *a, **kw)

        with patch("builtins.__import__", side_effect=_inject):
            meta = ident._extract_from_pdf_content(b"%PDF")

        assert meta["title"] == "Meta Title"
        assert meta["author"] == "John Doe"
        assert meta["year"] == 2019


class TestIdentifierURLMetadata:

    def test_html_page(self):
        ident = IdentifierModule()
        html = """
        <html>
          <head><title>My Very Long Paper Title - PDF Download</title></head>
          <body>
            <div class="authors">By Alice Smith, Bob Jones</div>
            <p>Published 2021.</p>
          </body>
        </html>
        """
        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(content=html.encode(),
                                               headers={"content-type": "text/html"})):
            meta = ident._extract_metadata_from_url("https://example.com/page")

        assert meta["title"] == "My Very Long Paper Title"
        assert meta["year"] == 2021
        assert "Alice Smith" in meta["author"]

    def test_pdf_delegates_to_extractor(self):
        ident = IdentifierModule()

        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(content=b"%PDF",
                                               headers={"content-type": "application/pdf"})), \
             patch.object(ident, "_extract_from_pdf_content",
                          return_value={"title": "T"}) as m:
            meta = ident._extract_metadata_from_url("https://example.com/file.pdf")

        assert meta == {"title": "T"}
        assert m.called


# ===================================================================
# Crossref searches
# ===================================================================

class TestIdentifierCrossref:

    def test_resolve_doi_via_title(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            return DummyResponse(json_data={"message": {"items": [
                {"title": ["Deep Learning"], "DOI": "10.1000/abc",
                 "author": [{"given": "Ian", "family": "Goodfellow"}],
                 "container-title": ["Nature"],
                 "published-print": {"date-parts": [[2016]]},
                 "is-referenced-by-count": 10},
                {"title": ["Other"], "DOI": "10.1000/def"},
            ]}})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            r = ident._resolve_doi_via_crossref_title("Deep Learning", "Deep Learning 2016")

        assert r["doi"] == "10.1000/abc"
        assert r["source"] == "crossref"

    def test_dedup_and_event_and_book(self):
        """Two Crossref pages: first returns a proceedings-article, second adds
        a duplicate + a book.  We should get exactly 2 unique results."""
        ident = IdentifierModule()
        call_n = {"n": 0}

        def fake_get(url, *a, **kw):
            call_n["n"] += 1
            if call_n["n"] == 1:
                return DummyResponse(json_data={"message": {"items": [{
                    "DOI": "10.1111/aaa", "title": ["Paper A"],
                    "type": "proceedings-article",
                    "author": [{"given": "A", "family": "B"}],
                    "event": {"name": ["NeurIPS"]},
                    "issued": {"date-parts": [[2020]]},
                    "is-referenced-by-count": 5, "publisher": "P",
                }]}})
            if call_n["n"] == 2:
                return DummyResponse(json_data={"message": {"items": [
                    {"DOI": "10.1111/aaa", "title": ["Paper A"],
                     "type": "proceedings-article"},  # dup
                    {"DOI": "10.2222/book", "title": ["A Great Book"],
                     "type": "book", "ISBN": ["9780000000001"],
                     "publisher": "Wiley",
                     "author": [{"given": "C", "family": "D"}],
                     "published-online": {"date-parts": [[2018]]}},
                ]}})
            return DummyResponse(json_data={"message": {"items": []}})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            results = ident._search_crossref("query", limit=10)

        assert len(results) == 2
        assert {r["doi"] for r in results} == {"10.1111/aaa", "10.2222/book"}
        conf = next(r for r in results if r["doi"] == "10.1111/aaa")
        assert conf["journal"] == "NeurIPS"
        book = next(r for r in results if r["doi"] == "10.2222/book")
        assert book["is_book"] is True
        assert book["isbn"] == "9780000000001"


# ===================================================================
# Google Books
# ===================================================================

class TestIdentifierGoogleBooks:

    def test_edition_and_isbn(self):
        ident = IdentifierModule()
        captured = {}

        def fake_get(url, *a, **kw):
            captured["params"] = kw.get("params")
            return DummyResponse(json_data={"items": [{
                "volumeInfo": {
                    "title": "Deep Learning", "subtitle": "2nd edition",
                    "authors": ["John Doe"],
                    "publisher": "Cambridge University Press",
                    "publishedDate": "2020-01-01",
                    "industryIdentifiers": [
                        {"type": "ISBN_13", "identifier": "9780000000001"}],
                    "pageCount": 500,
                    "infoLink": "https://books.example/book",
                },
            }]})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            results = ident._search_google_books(
                "Doe, J. (2020). Deep Learning (2nd ed.). Cambridge University Press.")

        assert len(results) == 1
        assert results[0]["is_book"] is True
        assert results[0]["isbn"] == "9780000000001"
        assert results[0]["edition"] == "2"
        assert "q" in captured["params"]


# ===================================================================
# Google Scholar (threaded, needs special mocking)
# ===================================================================

class TestIdentifierGoogleScholar:

    def test_success(self):
        ident = IdentifierModule(use_google_scholar=True)
        pubs = [{
            "bib": {"title": "NeurIPS Paper",
                    "author": "Doe, John and Smith, Alice",
                    "pub_year": "2019", "venue": "NeurIPS"},
            "num_citations": 12,
            "pub_url": "https://doi.org/10.9999/xyz",
            "eprint": "arXiv:1706.03762",
        }]

        fake_scholarly = MagicMock()
        fake_scholarly.search_pubs = MagicMock(return_value=pubs)
        with patch.object(_pipeline_mod, "scholarly", fake_scholarly), \
             patch("threading.Thread", ImmediateThread), \
             patch("time.sleep"), patch("time.time", return_value=1000.0):
            results = ident._search_google_scholar("neurips paper", limit=1)

        assert results[0]["source"] == "google_scholar"
        assert results[0]["doi"] == "10.9999/xyz"
        assert results[0]["arxiv_id"] == "1706.03762"
        assert results[0]["type"] == "conference"

    def test_captcha_returns_empty(self):
        ident = IdentifierModule(use_google_scholar=True)
        fake_scholarly = MagicMock()
        fake_scholarly.search_pubs = MagicMock(side_effect=Exception("captcha blocked"))
        with patch.object(_pipeline_mod, "scholarly", fake_scholarly), \
             patch("threading.Thread", ImmediateThread), \
             patch("time.sleep"), patch("time.time", return_value=1000.0):
            assert ident._search_google_scholar("q", limit=1) == []

    def test_timeout_returns_empty(self):
        ident = IdentifierModule(use_google_scholar=True)
        with patch("threading.Thread", NoopThread), \
             patch("time.sleep"), patch("time.time", return_value=1000.0):
            assert ident._search_google_scholar("q", limit=1) == []


# ===================================================================
# Fuzzy search
# ===================================================================

class TestIdentifierFuzzySearch:

    def test_no_hardcoded_well_known_papers(self):
        """fix #19: IdentifierModule must not have a well_known_papers shortcut."""
        ident = IdentifierModule()
        assert not hasattr(ident, 'well_known_papers'), (
            "well_known_papers shortcut should have been removed (#19)")

    def test_attention_query_goes_through_normal_search(self):
        """fix #19: 'attention is all you need' must go through normal multi-source search."""
        ident = IdentifierModule()
        entry = {"id": 1, "raw_text": "Attention is all you need",
                 "query_string": "Attention is all you need"}
        arxiv_result = {"source": "arxiv", "arxiv_id": "1706.03762",
                        "doi": "10.48550/arXiv.1706.03762",
                        "title": "Attention Is All You Need",
                        "url": "https://arxiv.org/abs/1706.03762"}
        with patch.object(ident, "_search_crossref", return_value=[arxiv_result]):
            r = ident._fuzzy_search(entry, lambda _: -1)
        assert r["status"] == "identified"

    def test_pmid_shortcut(self):
        ident = IdentifierModule()
        entry = {"id": 2, "raw_text": "PMID:12345678",
                 "query_string": "PMID:12345678"}
        with patch.object(ident, "_search_pubmed_by_id",
                          return_value={"source": "pubmed", "doi": "10.1234/pmid",
                                        "url": "https://example.com"}):
            r = ident._fuzzy_search(entry, lambda _: -1)
        assert r["status"] == "identified"
        assert r["doi"] == "10.1234/pmid"

    def test_book_prefers_google_books(self):
        ident = IdentifierModule()
        entry = {"id": 3,
                 "raw_text": "Doe, J. (2020). Deep Learning (2nd ed.). Wiley.",
                 "query_string": "Doe, J. (2020). Deep Learning (2nd ed.). Wiley."}

        gb = {"source": "google_books", "is_book": True, "type": "book",
              "title": "Deep Learning", "authors": ["John Doe"],
              "publisher": "Wiley", "year": 2020,
              "url": "https://books.example/book", "citations": 0,
              "is_primary_google_books_match": True}
        cr = {"source": "crossref", "doi": "10.0000/low", "title": "Unrelated",
              "authors": ["Someone"], "year": 2020, "journal": "",
              "citations": 0, "type": "book", "publisher": "Wiley"}

        with patch.object(ident, "_search_google_books", return_value=[gb]), \
             patch.object(ident, "_search_crossref", return_value=[cr]):
            r = ident._fuzzy_search(entry, lambda _: -1)

        assert r["status"] == "identified"
        assert r["metadata"]["source"] == "google_books"

    def test_interactive_user_picks_second(self):
        ident = IdentifierModule()
        entry = {"id": 4, "raw_text": "Some query", "query_string": "Some query"}
        scored = [
            {"source": "crossref", "doi": "10.1/a", "title": "A",
             "match_score": 75, "url": "https://doi.org/10.1/a"},
            {"source": "crossref", "doi": "10.1/b", "title": "B",
             "match_score": 74, "url": "https://doi.org/10.1/b"},
        ]

        with patch.object(ident, "_search_crossref", return_value=[{"doi": "10.1/a"}]), \
             patch.object(ident, "_score_candidates", return_value=scored):
            r = ident._fuzzy_search(entry, lambda c: 1)  # pick index 1

        assert r["status"] == "identified"
        assert r["doi"] == "10.1/b"


# ===================================================================
# Thesis detection
# ===================================================================

class TestIdentifierThesis:

    def test_base_search(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            return DummyResponse(json_data={"response": {"docs": [{
                "dctitle": ["Thesis Title"],
                "dcauthor": ["Doe, John"],
                "dcyear": ["2020"],
                "dccreator": ["Test University"],
                "dclink": ["https://example.com/thesis"],
            }]}})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            r = ident._search_base_for_thesis("Some Thesis PhD dissertation", year=2020)

        assert r["source"] == "base_search"
        assert r["type"] == "thesis"
        assert r["title"] == "Thesis Title"

    def test_openaire_search(self):
        ident = IdentifierModule()

        def fake_get(url, *a, **kw):
            return DummyResponse(json_data={"response": {"results": {"result": [{
                "metadata": {"oaf:entity": {"oaf:result": {
                    "title": {"$": "external providerRE Thesis"},
                    "creator": [{"$": "Doe, John"}],
                    "dateofacceptance": {"$": "2021-01-01"},
                    "publisher": {"$": "external providerRE University"},
                    "children": {"instance": [{"webresource": {
                        "url": {"$": "https://example.com/openaire"}}}]},
                }}}
            }]}}})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            r = ident._search_openaire_for_thesis("external providerRE Thesis", year=2021)

        assert r["source"] == "openaire"
        assert r["title"] == "external providerRE Thesis"
        assert r["school"] == "external providerRE University"
        assert r["url"] == "https://example.com/openaire"

    def test_openaire_via_detect_thesis(self):
        ident = IdentifierModule()
        with patch.object(ident, "_search_openaire_for_thesis",
                          return_value={"source": "openaire", "title": "Great Work",
                                        "authors": ["X"], "year": "2020",
                                        "school": "U", "url": "http://u",
                                        "type": "thesis"}):
            t = ident._detect_thesis(
                "Smith, J. (2020). Great Work. PhD thesis. Stanford University.")

        assert t["is_thesis"] is True
        assert t["thesis_type"] == "phdthesis"
        assert t["authors"] == ["Smith, J."]

    def test_manual_fallback(self):
        """When both external providerRE and BASE return nothing we parse the text ourselves."""
        ident = IdentifierModule()
        with patch.object(ident, "_search_openaire_for_thesis", return_value=None), \
             patch.object(ident, "_search_base_for_thesis", return_value=None):
            t = ident._detect_thesis(
                "Doe, J. (2020). Great Thesis. PhD thesis. Test University.")

        assert t["source"] == "manual"
        assert t["is_thesis"] is True
        assert t["thesis_type"] == "phdthesis"


# ===================================================================
# DataCite
# ===================================================================

class TestIdentifierDataCite:

    def test_success(self):
        ident = IdentifierModule()
        payload = {"data": {"attributes": {
            "titles": [{"title": "My Dataset"}],
            "creators": [{"name": "Doe, Jane"}],
            "publicationYear": 2022, "publisher": "Zenodo",
            "url": "https://doi.org/10.1234/data",
            "types": {"resourceTypeGeneral": "Dataset"},
        }}}

        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(json_data=payload)):
            r = ident._query_datacite("10.1234/data")

        assert r["title"] == "My Dataset"
        assert r["source"] == "datacite"
        assert r["year"] == 2022
        assert "Doe, Jane" in r["authors"]

    def test_404_returns_none(self):
        ident = IdentifierModule()
        with patch("onecite.pipeline.requests.get",
                    return_value=DummyResponse(status_code=404)):
            assert ident._query_datacite("10.9999/missing") is None


# ===================================================================
# EnricherModule
# ===================================================================

class TestEnricher:

    def test_convert_dataset(self):
        e = EnricherModule(use_google_scholar=False)
        c = e._convert_search_metadata({
            "source": "zenodo", "type": "dataset", "title": "T",
            "authors": ["A"], "year": 2020, "publisher": "Zenodo",
            "url": "https://example.com", "version": "1",
        })
        assert c["howpublished"] == "Zenodo"
        assert c["author"] == "A"

    def test_bibtex_key_generation(self):
        e = EnricherModule(use_google_scholar=False)
        key = e._generate_bibtex_key(
            {"author": "Doe, John and Smith, Alice", "year": "2020", "title": "Deep Learning"})
        assert key == "Doe2020Deep"

    def test_strip_html(self):
        e = EnricherModule(use_google_scholar=False)
        assert e._strip_html_tags("Human-level <i>control</i> &amp; learning") == \
               "Human-level control & learning"

    def test_semantic_scholar_429_returns_empty(self):
        """fix #25: 429 from Semantic Scholar must return [] without raising."""
        ident = IdentifierModule()
        resp = DummyResponse(status_code=429, json_data={})
        with patch("onecite.pipeline.requests.get", return_value=resp):
            result = ident._search_semantic_scholar("attention is all you need")
        assert result == []

    def test_crossref_request_has_user_agent_and_mailto(self):
        """fix #21: _get_crossref_metadata must send User-Agent and mailto."""
        e = EnricherModule(use_google_scholar=False)
        captured = {}

        def fake_get(url, *a, **kw):
            captured['headers'] = kw.get('headers', {})
            captured['params'] = kw.get('params', {})
            return DummyResponse(json_data={"message": {
                "DOI": "10.1234/x", "title": ["T"],
                "published-print": {"date-parts": [[2020]]},
            }})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            e._get_crossref_metadata("10.1234/x")

        assert "User-Agent" in captured["headers"], "User-Agent header missing"
        assert "OneCite" in captured["headers"]["User-Agent"]
        assert captured["params"].get("mailto"), "mailto param missing"

    def test_format_authors_name_field(self):
        """fix #22: org authors with 'name' field must not be dropped."""
        e = EnricherModule(use_google_scholar=False)
        authors = [
            {"given": "John", "family": "Doe"},
            {"name": "World Health Organization"},
            {"family": "Smith"},
            {"given": "Alice"},
        ]
        result = e._format_authors(authors)
        assert "Doe, John" in result
        assert "World Health Organization" in result
        assert "Smith" in result
        assert "Alice" in result

    def test_google_scholar_disabled_returns_none(self):
        e = EnricherModule(use_google_scholar=False)
        assert e._fetch_missing_field("pages", ["google_scholar_scraper"], {"title": "T"}) is None

    def test_convert_book(self):
        e = EnricherModule()
        r = e._convert_search_metadata({
            "title": "Deep Learning", "authors": ["Ian Goodfellow"],
            "year": 2016, "publisher": "MIT Press", "type": "book",
            "is_book": True, "edition": "1st", "isbn": "978-0262035613",
            "address": "Cambridge, MA",
        })
        assert "Goodfellow" in r["author"]
        assert r["publisher"] == "MIT Press"
        assert r["edition"] == "1st"
        assert r["isbn"] == "978-0262035613"

    def test_convert_conference(self):
        e = EnricherModule()
        r = e._convert_search_metadata({
            "title": "Attention Is All You Need", "authors": ["Ashish Vaswani"],
            "year": 2017, "journal": "Proceedings of NeurIPS", "type": "conference",
        })
        assert "booktitle" in r
        assert "Vaswani" in r["author"]

    def test_convert_dataset_with_version(self):
        e = EnricherModule()
        r = e._convert_search_metadata({
            "title": "ImageNet", "authors": ["Jia Deng"], "year": 2009,
            "type": "dataset", "is_dataset": True,
            "url": "https://example.com", "version": "1.0",
        })
        assert r["url"] == "https://example.com"
        assert r["version"] == "1.0"

    def test_convert_thesis(self):
        e = EnricherModule()
        r = e._convert_search_metadata({
            "title": "Neural Arch Search", "authors": ["John Smith"],
            "year": 2020, "type": "phdthesis", "is_thesis": True,
            "school": "Stanford University", "url": "https://example.com/thesis",
            "thesis_type": "phdthesis",
        })
        assert r["school"] == "Stanford University"
        assert r["type"] == "phdthesis"

    def test_convert_authors_as_string(self):
        e = EnricherModule()
        r = e._convert_search_metadata({
            "title": "Some Paper",
            "authors": "LeCun, Yann and Bengio, Yoshua",
            "year": 2020, "journal": "Nature",
        })
        assert "LeCun" in r["author"]

    def test_bibtex_key_dedup(self):
        """Two papers by the same first author in the same year should get
        distinct keys (Smith2020Deep vs Smith2020Deepa)."""
        e = EnricherModule()
        k1 = e._generate_bibtex_key({"author": "Smith, John", "year": "2020", "title": "Deep stuff"})
        k2 = e._generate_bibtex_key({"author": "Smith, John", "year": "2020", "title": "Deep things"})
        assert k1 == "Smith2020Deep"
        assert k2 == "Smith2020Deepa"

    def test_google_scholar_fetch_success(self):
        e = EnricherModule(use_google_scholar=True)

        def _pubs(_q):
            yield {"pages": "123--130"}

        fake_scholarly = MagicMock()
        fake_scholarly.search_pubs = MagicMock(side_effect=_pubs)
        with patch.object(_pipeline_mod, "scholarly", fake_scholarly), \
             patch("threading.Thread", ImmediateThread), \
             patch("time.sleep"), patch("time.time", return_value=1000.0):
            val = e._fetch_missing_field("pages", ["google_scholar_scraper"],
                                         {"title": "T", "author": "Doe, John", "year": "2020"})

        assert val == "123--130"

    def test_google_scholar_timeout(self):
        e = EnricherModule(use_google_scholar=True)
        with patch("threading.Thread", NoopThread), \
             patch("time.sleep"), patch("time.time", return_value=1000.0):
            assert e._fetch_from_google_scholar("pages", {"title": "T"}) is None

    def test_google_scholar_worker_error(self):
        e = EnricherModule(use_google_scholar=True)
        fake_scholarly = MagicMock()
        fake_scholarly.search_pubs = MagicMock(side_effect=RuntimeError("boom"))
        with patch.object(_pipeline_mod, "scholarly", fake_scholarly), \
             patch("threading.Thread", ImmediateThread), \
             patch("time.sleep"), patch("time.time", return_value=1000.0):
            assert e._fetch_from_google_scholar("pages", {"title": "T"}) is None

    def test_strip_html_jats_and_entities(self):
        """JATS tags replaced with space (no word merging); double-escaped entities decoded."""
        e = EnricherModule(use_google_scholar=False)
        jats = "<jats:title>Background</jats:title><jats:p>The treatment.</jats:p>"
        result = e._strip_html_tags(jats)
        assert "Background" in result and "The treatment" in result
        assert "BackgroundThe" not in result
        text = "p &amp;gt; 0.05 and p &amp;lt; 0.01"
        result2 = e._strip_html_tags(text)
        assert "&gt;" not in result2 and ">" in result2
        assert "&lt;" not in result2 and "<" in result2

    def test_crossref_metadata_abstract(self):
        """Abstract extracted and JATS-cleaned when present; absent when Crossref omits it."""
        e = EnricherModule(use_google_scholar=False)
        payload_with = {"message": {
            "DOI": "10.1234/test", "title": ["Test Article"],
            "author": [{"given": "Jane", "family": "Doe"}],
            "container-title": ["Test Journal"],
            "published-print": {"date-parts": [[2023]]},
            "abstract": "<jats:p>This is the <jats:italic>abstract</jats:italic> text.</jats:p>",
        }}
        with patch("onecite.pipeline.requests.get",
                   return_value=DummyResponse(json_data=payload_with)):
            meta = e._get_crossref_metadata("10.1234/test")
        assert "abstract" in meta and "abstract" in meta["abstract"]
        assert "<jats:" not in meta["abstract"]

        payload_without = {"message": {
            "DOI": "10.1234/noabs", "title": ["No Abstract"],
            "author": [{"given": "A", "family": "B"}],
            "container-title": ["J"],
            "published-print": {"date-parts": [[2020]]},
        }}
        with patch("onecite.pipeline.requests.get",
                   return_value=DummyResponse(json_data=payload_without)):
            assert "abstract" not in e._get_crossref_metadata("10.1234/noabs")

    def test_get_pubmed_abstract_via_doi(self):
        """_get_pubmed_abstract resolves DOI → PMID → fetches abstract."""
        e = EnricherModule(use_google_scholar=False)
        xml_content = b"""<?xml version="1.0"?>
        <PubmedArticleSet><PubmedArticle><MedlineCitation>
          <Article><Abstract>
            <AbstractText>This is the PubMed abstract.</AbstractText>
          </Abstract></Article>
        </MedlineCitation></PubmedArticle></PubmedArticleSet>"""

        def fake_get(url, *a, **kw):
            params = kw.get("params", {})
            if "esearch" in url:
                return DummyResponse(json_data={
                    "esearchresult": {"idlist": ["12345678"]}
                })
            if "efetch" in url:
                return DummyResponse(content=xml_content)
            return DummyResponse(status_code=404, json_data={})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            result = e._get_pubmed_abstract({"doi": "10.1234/test"})

        assert result == "This is the PubMed abstract."

    def test_get_pubmed_abstract_structured(self):
        """Structured abstracts (multiple AbstractText with Label) are joined."""
        e = EnricherModule(use_google_scholar=False)
        xml_content = b"""<?xml version="1.0"?>
        <PubmedArticleSet><PubmedArticle><MedlineCitation>
          <Article><Abstract>
            <AbstractText Label="BACKGROUND">Background text.</AbstractText>
            <AbstractText Label="METHODS">Methods text.</AbstractText>
            <AbstractText Label="RESULTS">Results text.</AbstractText>
          </Abstract></Article>
        </MedlineCitation></PubmedArticle></PubmedArticleSet>"""

        def fake_get(url, *a, **kw):
            if "esearch" in url:
                return DummyResponse(json_data={"esearchresult": {"idlist": ["99999"]}})
            if "efetch" in url:
                return DummyResponse(content=xml_content)
            return DummyResponse(status_code=404, json_data={})

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            result = e._get_pubmed_abstract({"doi": "10.1234/struct"})

        assert result is not None
        assert "BACKGROUND: Background text." in result
        assert "METHODS: Methods text." in result
        assert "RESULTS: Results text." in result

    def test_get_pubmed_abstract_returns_none(self):
        """Returns None when PMID not found, or when PubMed record has no Abstract."""
        e = EnricherModule(use_google_scholar=False)

        with patch("onecite.pipeline.requests.get",
                   return_value=DummyResponse(json_data={"esearchresult": {"idlist": []}})):
            assert e._get_pubmed_abstract({"doi": "10.9999/notinpubmed"}) is None

        xml_no_abstract = b"""<?xml version="1.0"?>
        <PubmedArticleSet><PubmedArticle><MedlineCitation>
          <Article><ArticleTitle>No abstract here</ArticleTitle></Article>
        </MedlineCitation></PubmedArticle></PubmedArticleSet>"""

        def fake_get(url, *a, **kw):
            if "esearch" in url:
                return DummyResponse(json_data={"esearchresult": {"idlist": ["77777"]}})
            return DummyResponse(content=xml_no_abstract)

        with patch("onecite.pipeline.requests.get", side_effect=fake_get):
            assert e._get_pubmed_abstract({"doi": "10.1234/noabs"}) is None

    def test_fetch_missing_field_abstract_sources(self):
        """pubmed_api delegates to _get_pubmed_abstract; crossref_api is always skipped."""
        e = EnricherModule(use_google_scholar=False)
        with patch.object(e, "_get_pubmed_abstract", return_value="Mocked abstract") as m:
            val = e._fetch_missing_field("abstract", ["pubmed_api"], {"doi": "10.1/x"})
        assert val == "Mocked abstract"
        m.assert_called_once_with({"doi": "10.1/x"})

        with patch.object(e, "_get_pubmed_abstract", return_value=None) as m:
            assert e._fetch_missing_field("abstract", ["crossref_api"], {"doi": "10.1/x"}) is None
        m.assert_not_called()


# ===================================================================
# FormatterModule
# ===================================================================

class TestFormatter:

    def test_latex_escaping(self):
        fmt = FormatterModule()
        # Already-escaped sequences must survive untouched
        assert fmt._escape_latex_chars(r"K{\\\"u}nsch") == r"K{\\\"u}nsch"
        escaped = fmt._escape_latex_chars("Müller")
        assert "ü" not in escaped
        assert escaped.startswith("M{")

    def test_all_three_formats(self):
        fmt = FormatterModule()
        entry = {
            "id": 1, "doi": "10.1234/xyz", "status": "completed",
            "bib_key": "Doe2020Deep",
            "bib_data": {
                "ENTRYTYPE": "article", "ID": "Doe2020Deep",
                "author": "Doe, John and Smith, Alice",
                "title": "Deep Learning", "journal": "Nature",
                "year": 2020, "volume": "1", "number": "2",
                "pages": "3--4", "doi": "10.1234/xyz",
            },
        }
        for of in ("bibtex", "apa", "mla"):
            r = fmt.format([entry], of)
            assert r["report"]["succeeded"] == 1, f"{of} failed"

    def test_failed_entry_counted(self):
        fmt = FormatterModule()
        entry = {"id": 1, "doi": "", "status": "enrichment_failed",
                 "bib_key": "", "bib_data": {}}
        r = fmt.format([entry], "bibtex")
        assert r["report"]["succeeded"] == 0
        assert len(r["report"]["failed_entries"]) == 1

    def test_mla_book_italics(self):
        fmt = FormatterModule()
        entry = {
            "id": 1, "doi": "", "status": "completed",
            "bib_key": "Goodfellow2016",
            "bib_data": {"ENTRYTYPE": "book", "title": "Deep Learning",
                         "author": "Goodfellow, Ian and Bengio, Yoshua",
                         "publisher": "MIT Press", "year": "2016"},
        }
        out = fmt._format_mla(entry)
        assert "*Deep Learning*" in out
        assert "MIT Press" in out

    def test_mla_article_quotes(self):
        fmt = FormatterModule()
        entry = {
            "id": 1, "doi": "10.1234/test", "status": "completed",
            "bib_key": "Test2020",
            "bib_data": {"ENTRYTYPE": "article", "title": "A Test Paper",
                         "author": "Smith, John and Doe, Jane",
                         "journal": "Nature", "year": "2020",
                         "volume": "580", "pages": "1-10",
                         "doi": "10.1234/test"},
        }
        out = fmt._format_mla(entry)
        assert '"A Test Paper."' in out
        assert "Nature" in out
        assert "doi:10.1234/test" in out

    def test_mla_single_author(self):
        fmt = FormatterModule()
        entry = {
            "id": 1, "doi": "", "status": "completed",
            "bib_key": "Solo2021",
            "bib_data": {"ENTRYTYPE": "article", "title": "Solo Work",
                         "author": "Solo, Han", "journal": "J. Test",
                         "year": "2021"},
        }
        assert "Solo, Han." in fmt._format_mla(entry)

    def test_unsupported_format_raises_format_error(self):
        """fix #13: unsupported output_format must raise FormatError, not silently use bibtex."""
        from onecite.exceptions import FormatError
        fmt = FormatterModule()
        entry = {
            "id": 1, "doi": "10.1/x", "status": "completed",
            "bib_key": "K", "bib_data": {"ENTRYTYPE": "article", "ID": "K", "title": "T"},
        }
        r = fmt.format([entry], "ris")
        assert len(r["report"]["failed_entries"]) == 1
        assert "Unsupported output format" in r["report"]["failed_entries"][0]["error"]

    def test_no_placeholder_in_thesis_fallback(self):
        """fix #24: manual thesis fallback must not inject Unknown Title/University."""
        ident = IdentifierModule()
        with patch.object(ident, "_search_openaire_for_thesis", return_value=None), \
             patch.object(ident, "_search_base_for_thesis", return_value=None):
            result = ident._detect_thesis(
                "Smith, J. (2020). Neural Architecture Search. PhD Thesis. Stanford University."
            )
        if result:
            assert result.get("title") != "Unknown Title"
            assert result.get("school") != "Unknown University"
            assert "Unknown Author" not in str(result.get("authors", []))

    def test_process_references_empty_input_raises(self):
        """fix #13/#24: empty input_content raises ValidationError."""
        from onecite.exceptions import ValidationError
        from onecite.core import process_references
        import pytest
        with pytest.raises(ValidationError):
            process_references("", "txt", "journal_article_full", "bibtex", lambda c: -1)
        with pytest.raises(ValidationError):
            process_references("   ", "txt", "journal_article_full", "bibtex", lambda c: -1)

    def test_unknown_format_raises_in_failed_entries(self):
        """fix #13: unknown format results in failed entry, not silent bibtex fallback."""
        fmt = FormatterModule()
        entry = {
            "id": 1, "doi": "10.1234/x", "status": "completed",
            "bib_key": "Test2020",
            "bib_data": {"ENTRYTYPE": "article", "title": "Test",
                         "author": "Author, A", "year": "2020"},
        }
        r = fmt.format([entry], "unknown_format")
        assert r["report"]["succeeded"] == 0
        assert len(r["report"]["failed_entries"]) == 1


# ===================================================================
# Helpers
# ===================================================================

class TestSafeYear:

    def test_normal(self):
        from onecite.pipeline import _safe_year
        assert _safe_year({"date-parts": [[2021, 3, 1]]}) == 2021

    def test_empty_inner(self):
        from onecite.pipeline import _safe_year
        assert _safe_year({"date-parts": [[]]}) is None

    def test_missing(self):
        from onecite.pipeline import _safe_year
        assert _safe_year(None) is None
        assert _safe_year({}) is None
