"""Circuit-breaker, parallel fan-out, and health-aware tie-break behavior.

The breaker exists so a persistently failing source degrades one disclosed
source instead of stalling every entry of a batch; the parallel collector
bounds suggest latency by the slowest source instead of the sum of sources;
and the scorer prefers a healthy source's candidate at equal lexical
evidence. HTTP is replaced at the ``requests.get`` boundary throughout.
"""

import time as real_time
from unittest.mock import patch

import requests

from onecite.pipeline.identifier import IdentifierModule
from onecite.pipeline.source_health import SourceCircuitBreaker

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


def _zero_response(url):
    if "api.crossref.org" in url:
        return _Response(json_data={"message": {"items": []}})
    if "semanticscholar" in url:
        return _Response(json_data={"data": []})
    if "export.arxiv.org" in url:
        return _Response(content=EMPTY_ARXIV_FEED)
    raise AssertionError(f"Unexpected URL: {url}")


def _source_map(suggestion):
    return {item["source"]: item["status"] for item in suggestion["sources"]}


class _FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_breaker_opens_after_threshold_and_recovers_via_half_open_probe():
    clock = _FakeClock()
    breaker = SourceCircuitBreaker(failure_threshold=2, cooldown_seconds=120.0, clock=clock)

    assert breaker.allow("s2")
    breaker.record_failure("s2")
    assert breaker.allow("s2")  # one failure is below the threshold
    breaker.record_failure("s2")
    assert not breaker.allow("s2")  # open
    assert breaker.is_open("s2")

    clock.now += 119.0
    assert not breaker.allow("s2")  # still cooling down

    clock.now += 2.0
    assert breaker.allow("s2")  # half-open probe
    assert not breaker.allow("s2")  # only one concurrent probe
    breaker.record_failure("s2")  # probe failed -> re-open immediately
    assert not breaker.allow("s2")

    clock.now += 121.0
    assert breaker.allow("s2")
    breaker.record_success("s2")  # probe succeeded -> fully closed
    assert breaker.allow("s2")
    assert not breaker.is_open("s2")


def test_success_resets_consecutive_failure_count():
    breaker = SourceCircuitBreaker(failure_threshold=2, cooldown_seconds=120.0)
    breaker.record_failure("crossref")
    breaker.record_success("crossref")
    breaker.record_failure("crossref")
    assert breaker.allow("crossref")  # never reached two consecutive failures


def test_batch_skips_persistently_failing_source_and_discloses_it():
    clock = _FakeClock()
    breaker = SourceCircuitBreaker(failure_threshold=2, cooldown_seconds=120.0, clock=clock)
    identifier = IdentifierModule(source_breaker=breaker)
    s2_calls = 0

    def get(url, *args, **kwargs):
        nonlocal s2_calls
        if "semanticscholar" in url:
            s2_calls += 1
            return _Response(429)
        return _zero_response(url)

    def run(query):
        return identifier.suggest({"id": 1, "raw_text": query, "query_string": query})

    with (
        patch("onecite.pipeline.requests.get", side_effect=get),
        patch("onecite.pipeline.identifier.time.sleep"),
    ):
        first = run("entry one")
        second = run("entry two")
        calls_before_skip = s2_calls
        third = run("entry three")

    # Rounds one and two consult Semantic Scholar (four attempts each);
    # round three is short-circuited without a single HTTP call.
    assert calls_before_skip == 8
    assert s2_calls == calls_before_skip
    assert _source_map(first)["semantic_scholar"] == "rate_limited"
    assert _source_map(second)["semantic_scholar"] == "rate_limited"
    assert _source_map(third)["semantic_scholar"] == "skipped_unhealthy"
    assert third["status"] == "no_candidates_incomplete"
    # Healthy sources keep answering normally.
    assert _source_map(third)["crossref"] == "ok"
    assert _source_map(third)["arxiv"] == "ok"


def test_breaker_probes_again_after_cooldown_and_closes_on_recovery():
    clock = _FakeClock()
    breaker = SourceCircuitBreaker(failure_threshold=2, cooldown_seconds=120.0, clock=clock)
    identifier = IdentifierModule(source_breaker=breaker)
    s2_failing = True
    s2_calls = 0

    def get(url, *args, **kwargs):
        nonlocal s2_calls
        if "semanticscholar" in url:
            s2_calls += 1
            if s2_failing:
                return _Response(429)
            return _Response(json_data={"data": []})
        return _zero_response(url)

    def run(query):
        return identifier.suggest({"id": 1, "raw_text": query, "query_string": query})

    with (
        patch("onecite.pipeline.requests.get", side_effect=get),
        patch("onecite.pipeline.identifier.time.sleep"),
    ):
        run("entry one")
        run("entry two")  # breaker opens
        assert _source_map(run("entry three"))["semantic_scholar"] == "skipped_unhealthy"

        clock.now += 121.0
        s2_failing = False
        recovered = run("entry four")  # half-open probe succeeds
        after = run("entry five")

    assert _source_map(recovered)["semantic_scholar"] == "ok"
    assert _source_map(after)["semantic_scholar"] == "ok"


def test_suggestion_sources_are_queried_concurrently():
    identifier = IdentifierModule()

    def slow_get(url, *args, **kwargs):
        real_time.sleep(0.15)
        return _zero_response(url)

    query = "an ordinary citation string"
    with patch("onecite.pipeline.requests.get", side_effect=slow_get):
        started = real_time.monotonic()
        suggestion = identifier.suggest({"id": 1, "raw_text": query, "query_string": query})
        elapsed = real_time.monotonic() - started

    assert set(_source_map(suggestion)) == {"crossref", "semantic_scholar", "arxiv"}
    # Crossref issues three zero-result strategies serially (>= 0.45 s on its
    # own); a serial collection would additionally pay Semantic Scholar and
    # arXiv in full (>= 0.75 s total). Concurrency keeps the whole collection
    # near the slowest single source.
    assert elapsed < 0.7, f"collection took {elapsed:.2f}s; sources appear serialized"


def test_merged_candidate_order_is_independent_of_completion_order():
    identifier = IdentifierModule()

    def get(url, *args, **kwargs):
        if "api.crossref.org" in url:
            real_time.sleep(0.2)  # slowest source finishes last
            return _Response(
                json_data={
                    "message": {
                        "items": [
                            {
                                "title": ["Crossref Candidate"],
                                "DOI": "10.1000/cr1",
                                "author": [{"given": "A", "family": "Author"}],
                                "issued": {"date-parts": [[2020]]},
                            }
                        ]
                    }
                }
            )
        if "semanticscholar" in url:
            return _Response(
                json_data={
                    "data": [
                        {
                            "title": "Semantic Candidate",
                            "year": 2020,
                            "authors": [{"name": "B Author"}],
                            "externalIds": {},
                        }
                    ]
                }
            )
        return _zero_response(url)

    with patch("onecite.pipeline.requests.get", side_effect=get):
        candidates = identifier._collect_suggestion_candidates("an ordinary citation string")
    sources_in_order = [candidate["source"] for candidate in candidates]
    # Crossref finished last but must still be merged first (frozen order).
    assert sources_in_order[0] == "crossref"
    assert sources_in_order[-1] == "semantic_scholar"
    assert set(sources_in_order) == {"crossref", "semantic_scholar"}


def test_tie_break_prefers_candidate_from_healthy_source():
    identifier = IdentifierModule()
    identifier._source_status = {"crossref": "rate_limited", "semantic_scholar": "ok"}
    shared = {
        "title": "Deep Learning",
        "authors": ["Yann LeCun"],
        "year": 2015,
        "_source_rank": 1,
    }
    degraded = {**shared, "source": "crossref"}
    healthy = {**shared, "source": "semantic_scholar"}

    ranked = identifier._score_candidates([degraded, healthy], "Deep Learning, LeCun, 2015")

    # Equal lexical evidence: the healthy source's candidate must win the tie
    # even though Crossref normally outranks Semantic Scholar on source tier.
    assert ranked[0]["source"] == "semantic_scholar"
    assert ranked[1]["source"] == "crossref"
