"""Frozen retry policy and truthful health for ``suggest`` sources.

These tests exercise the real suggestion collector with HTTP replaced at the
``requests.get`` boundary.  A valid empty response is a result, not a failure;
conditional sources appear only when routing actually consults them.
"""

from collections import Counter
from unittest.mock import patch

import pytest
import requests

from onecite.pipeline.identifier import IdentifierModule

EMPTY_ARXIV_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>
"""


class _Response:
    def __init__(self, status_code=200, json_data=None, content=b"", headers=None):
        self.status_code = status_code
        self._json_data = {} if json_data is None else json_data
        self.content = content
        self.headers = {} if headers is None else headers

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}", response=self)


SOURCE_CASES = [
    ("crossref", "_search_crossref", ("ordinary citation",)),
    ("semantic_scholar", "_search_semantic_scholar", ("ordinary citation",)),
    ("arxiv", "_search_arxiv_candidates", ("ordinary citation",)),
    ("pubmed", "_search_pubmed", ("clinical trial",)),
    ("google_books", "_search_google_books", ("ISBN 978-0-262-03561-3",)),
    ("openaire", "_search_openaire_for_thesis", ("A thesis title",)),
    ("base_search", "_search_base_for_thesis", ("A thesis title",)),
]


def _call_source(identifier, method_name, args):
    return getattr(identifier, method_name)(*args)


def _zero_response(url):
    if "api.crossref.org" in url:
        return _Response(json_data={"message": {"items": []}})
    if "semanticscholar" in url:
        return _Response(json_data={"data": []})
    if "export.arxiv.org" in url:
        return _Response(content=EMPTY_ARXIV_FEED)
    if "eutils.ncbi.nlm.nih.gov" in url:
        return _Response(json_data={"esearchresult": {"idlist": []}})
    if "googleapis.com/books" in url:
        return _Response(json_data={"items": []})
    if "api.openaire.eu" in url:
        return _Response(json_data={"response": {"results": {"result": []}}})
    if "api.base-search.net" in url:
        return _Response(json_data={"response": {"docs": []}})
    raise AssertionError(f"Unexpected URL: {url}")


def _source_map(suggestion):
    return {item["source"]: item["status"] for item in suggestion["sources"]}


@pytest.mark.parametrize(
    ("source_key", "method_name", "args"),
    SOURCE_CASES,
    ids=[case[0] for case in SOURCE_CASES],
)
def test_every_source_stops_after_four_persistent_429_attempts(source_key, method_name, args):
    identifier = IdentifierModule()

    with (
        patch("onecite.pipeline.requests.get", return_value=_Response(429)) as get_mock,
        patch("onecite.pipeline.identifier.time.sleep") as sleep_mock,
    ):
        _call_source(identifier, method_name, args)

    assert get_mock.call_count == 4
    assert [call.args[0] for call in sleep_mock.call_args_list] == [1.0, 3.0, 8.0]
    assert identifier._source_status == {source_key: "rate_limited"}


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_retryable_server_errors_share_the_four_attempt_policy(status_code):
    identifier = IdentifierModule()

    with (
        patch("onecite.pipeline.requests.get", return_value=_Response(status_code)) as get_mock,
        patch("onecite.pipeline.identifier.time.sleep") as sleep_mock,
    ):
        assert identifier._search_semantic_scholar("ordinary citation") == []

    assert get_mock.call_count == 4
    assert [call.args[0] for call in sleep_mock.call_args_list] == [1.0, 3.0, 8.0]
    assert identifier._source_status == {"semantic_scholar": "error"}


@pytest.mark.parametrize(
    "exception_type", [requests.exceptions.Timeout, requests.exceptions.ConnectionError]
)
def test_timeout_and_connection_or_dns_errors_are_retried_four_times(exception_type):
    identifier = IdentifierModule()

    with (
        patch(
            "onecite.pipeline.requests.get", side_effect=exception_type("network down")
        ) as get_mock,
        patch("onecite.pipeline.identifier.time.sleep") as sleep_mock,
    ):
        assert identifier._search_arxiv_candidates("ordinary citation") == []

    assert get_mock.call_count == 4
    assert [call.args[0] for call in sleep_mock.call_args_list] == [1.0, 3.0, 8.0]
    assert identifier._source_status == {"arxiv": "error"}


@pytest.mark.parametrize(
    ("query", "conditional_sources"),
    [
        ("ISBN 978-0-262-03561-3", {"google_books"}),
        ("A randomized controlled clinical trial", {"pubmed"}),
        ("A dissertation about citation matching", {"openaire", "base_search"}),
    ],
)
def test_valid_zero_results_are_not_retried_and_only_routed_sources_are_disclosed(
    query, conditional_sources
):
    identifier = IdentifierModule()
    calls = []

    def zero_get(url, *args, **kwargs):
        calls.append(url)
        return _zero_response(url)

    with (
        patch("onecite.pipeline.requests.get", side_effect=zero_get),
        patch("onecite.pipeline.identifier.time.sleep") as sleep_mock,
    ):
        suggestion = identifier.suggest({"id": 1, "raw_text": query, "query_string": query})

    source_status = _source_map(suggestion)
    expected_sources = {"crossref", "semantic_scholar", "arxiv"} | conditional_sources
    assert set(source_status) == expected_sources
    assert set(source_status.values()) == {"ok"}
    assert suggestion["status"] == "no_candidates"
    sleep_mock.assert_not_called()

    counts = Counter(
        (
            "crossref"
            if "api.crossref.org" in url
            else (
                "semantic_scholar"
                if "semanticscholar" in url
                else (
                    "arxiv"
                    if "export.arxiv.org" in url
                    else (
                        "pubmed"
                        if "eutils.ncbi.nlm.nih.gov" in url
                        else (
                            "google_books"
                            if "googleapis.com/books" in url
                            else "openaire" if "api.openaire.eu" in url else "base_search"
                        )
                    )
                )
            )
        )
        for url in calls
    )
    # Crossref broadens a genuine zero-result search with three distinct
    # strategies. Every other consulted source receives exactly one request.
    assert counts["crossref"] == 3
    for source in expected_sources - {"crossref"}:
        assert counts[source] == 1


def test_retry_after_is_honoured_capped_and_disclosed_end_to_end():
    identifier = IdentifierModule()
    openaire_calls = 0
    sleeps = []

    def get_with_openaire_throttled(url, *args, **kwargs):
        nonlocal openaire_calls
        if "api.openaire.eu" in url:
            openaire_calls += 1
            headers = {"Retry-After": "900"} if openaire_calls == 1 else {}
            return _Response(429, headers=headers)
        return _zero_response(url)

    query = "A dissertation about citation matching"
    with (
        patch("onecite.pipeline.requests.get", side_effect=get_with_openaire_throttled),
        patch(
            "onecite.pipeline.identifier.time.sleep",
            side_effect=lambda seconds: sleeps.append(seconds),
        ),
    ):
        suggestion = identifier.suggest({"id": 1, "raw_text": query, "query_string": query})

    assert openaire_calls == 4
    assert sleeps == [20.0, 3.0, 8.0]
    assert _source_map(suggestion) == {
        "arxiv": "ok",
        "base_search": "ok",
        "crossref": "ok",
        "openaire": "rate_limited",
        "semantic_scholar": "ok",
    }
    assert suggestion["status"] == "no_candidates_incomplete"


def test_base_is_not_marked_when_openaire_returns_a_thesis():
    identifier = IdentifierModule()
    calls = []
    openaire_payload = {
        "response": {
            "results": {
                "result": [
                    {
                        "metadata": {
                            "oaf:entity": {
                                "oaf:result": {
                                    "title": {"$": "Citation Matching Dissertation"},
                                    "creator": [{"$": "A. Researcher"}],
                                    "dateofacceptance": {"$": "2024-01-01"},
                                    "publisher": {"$": "Example University"},
                                    "children": {"instance": []},
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    def get_with_openaire_hit(url, *args, **kwargs):
        calls.append(url)
        if "api.openaire.eu" in url:
            return _Response(json_data=openaire_payload)
        return _zero_response(url)

    query = "Citation Matching Dissertation"
    with patch("onecite.pipeline.requests.get", side_effect=get_with_openaire_hit):
        suggestion = identifier.suggest({"id": 1, "raw_text": query, "query_string": query})

    assert "base_search" not in _source_map(suggestion)
    assert _source_map(suggestion)["openaire"] == "ok"
    assert not any("api.base-search.net" in url for url in calls)
