"""arXiv suggestion-source resilience and truthful health disclosure.

arXiv rate-limits aggressively but its 429s are short-lived: a brief backoff
must recover, and when the source stays throttled the disclosure must say
``rate_limited`` — reporting it as ``error`` would misstate source health to
callers deciding whether to retry. All tests run offline with mocks; the
success payload is the bundled Atom fixture, which mirrors the real API
shape.
"""

from unittest.mock import patch

from onecite.benchmarks.offline import ARXIV_TRANSFORMER
from onecite.pipeline.identifier import IdentifierModule


class _Response:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.content = text.encode("utf-8")
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(f"HTTP {self.status_code}", response=self)


_QUERY = "Attention is all you need, Vaswani et al., NIPS 2017"


def _search(responses, sleeps):
    identifier = IdentifierModule()
    identifier._source_status = {}
    urls = []

    def fake_get(url, *args, **kwargs):
        urls.append(url)
        return next(responses)

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        with patch(
            "onecite.pipeline.identifier.time.sleep", side_effect=lambda s: sleeps.append(s)
        ):
            results = identifier._search_arxiv_candidates(_QUERY)
    return results, identifier._source_status, urls


def test_recovers_from_transient_429_with_backoff():
    sleeps = []
    responses = iter([_Response(429), _Response(200, ARXIV_TRANSFORMER)])
    results, status, urls = _search(responses, sleeps)

    assert status == {"arxiv": "ok"}
    assert len(sleeps) == 1  # one backoff, then success
    # Strict field-level verification against the Atom payload.
    assert len(results) == 1
    candidate = results[0]
    assert candidate["title"] == "Attention Is All You Need"
    assert candidate["arxiv_id"] == "1706.03762"
    assert candidate["year"] == 2017
    assert candidate["authors"][0] == "Ashish Vaswani"
    assert candidate["url"] == "https://arxiv.org/abs/1706.03762"
    assert candidate["source"] == "arxiv"


def test_persistent_429_is_disclosed_as_rate_limited_not_error():
    sleeps = []
    responses = iter([_Response(429), _Response(429), _Response(429), _Response(429)])
    results, status, _ = _search(responses, sleeps)

    assert results == []
    assert status == {"arxiv": "rate_limited"}
    assert sleeps == [10.0, 60.0, 300.0]


def test_retry_after_takes_precedence_and_is_capped():
    sleeps = []
    responses = iter(
        [_Response(429, headers={"Retry-After": "900"}), _Response(200, ARXIV_TRANSFORMER)]
    )
    results, status, _ = _search(responses, sleeps)

    assert status == {"arxiv": "ok"}
    assert results
    assert sleeps == [600.0]


def test_transient_500_is_retried():
    sleeps = []
    responses = iter([_Response(500), _Response(200, ARXIV_TRANSFORMER)])
    results, status, _ = _search(responses, sleeps)

    assert status == {"arxiv": "ok"}
    assert len(results) == 1


def test_network_exception_is_disclosed_as_error():
    identifier = IdentifierModule()
    identifier._source_status = {}
    with patch("onecite.pipeline.requests.get", side_effect=ConnectionError("boom")):
        results = identifier._search_arxiv_candidates(_QUERY)
    assert results == []
    assert identifier._source_status == {"arxiv": "error"}


def test_queries_https_endpoint_directly():
    # The http endpoint 301-redirects to https, wasting a round-trip per
    # query and inflating the rate-limit pressure.
    sleeps = []
    responses = iter([_Response(200, ARXIV_TRANSFORMER)])
    _, _, urls = _search(responses, sleeps)
    assert urls == ["https://export.arxiv.org/api/query"]
