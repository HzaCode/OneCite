"""Source-health disclosure in suggest output.

`suggest` consults CrossRef and Semantic Scholar for every query. When one
of them is rate-limited or errors, the candidate list may silently miss the
correct match (Semantic Scholar covers venues CrossRef does not index, e.g.
NeurIPS). The output must disclose that instead of presenting an incomplete
list as exhaustive.
"""

from unittest.mock import patch

from onecite import suggest_references
from onecite.benchmarks.offline import offline_requests_get


def _suggest_offline(text):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return suggest_references(input_content=text, input_type="txt")


def test_healthy_sources_are_disclosed_as_ok():
    result = _suggest_offline("Attention is all you need, Vaswani et al., NIPS 2017")
    suggestion = result["suggestions"][0]
    assert suggestion["status"] == "candidates_found"
    sources = {item["source"]: item for item in suggestion["sources"]}
    assert sources["crossref"]["status"] == "ok"
    assert sources["semantic_scholar"]["status"] == "ok"
    assert sources["arxiv"]["status"] == "ok"
    # The fixture indexes the true NeurIPS paper via Semantic Scholar.
    assert sources["semantic_scholar"]["candidates"] >= 1


def test_arxiv_covers_venues_crossref_misses():
    # The top candidate for a famous NeurIPS citation must be the actual
    # paper, found via arXiv — CrossRef does not index NeurIPS proceedings.
    result = _suggest_offline("Attention is all you need, Vaswani et al., NIPS 2017")
    suggestion = result["suggestions"][0]
    arxiv_candidates = [c for c in suggestion["candidates"] if c["source"] == "arxiv"]
    assert arxiv_candidates
    assert arxiv_candidates[0]["title"] == "Attention Is All You Need"
    assert arxiv_candidates[0]["arxiv_id"] == "1706.03762"


def test_rate_limited_source_marks_suggestion_incomplete():
    class _RateLimited:
        status_code = 429
        text = ""

        def json(self):
            return {}

        def raise_for_status(self):
            pass

    def get_with_s2_down(url, *args, **kwargs):
        if "semanticscholar" in url:
            return _RateLimited()
        return offline_requests_get(url, *args, **kwargs)

    with patch.multiple("onecite.pipeline.requests", get=get_with_s2_down):
        with patch("onecite.pipeline.identifier.time.sleep") as sleep_mock:
            result = suggest_references(
                input_content="Attention is all you need, Vaswani et al., NIPS 2017",
                input_type="txt",
            )

    suggestion = result["suggestions"][0]
    sources = {item["source"]: item for item in suggestion["sources"]}
    assert sources["semantic_scholar"]["status"] == "rate_limited"
    assert sources["crossref"]["status"] == "ok"
    # CrossRef fixture still yields candidates, but the status must say the
    # list may be incomplete — this is the honest signal.
    assert suggestion["status"] == "candidates_found_incomplete"
    sleep_mock.assert_called()  # retried once before giving up


def test_bib_input_builds_structured_query_not_dict_repr():
    # A DOI-bearing BibTeX entry used to fall back to str(entry) — a Python
    # dict repr — as the search query sent to the scholarly indexes.
    bib = (
        "@article{k1, title={Attention Is All You Need}, "
        "author={Vaswani, Ashish}, year={2017}, doi={10.5555/3295222.3295349}}"
    )
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        result = suggest_references(input_content=bib, input_type="bib")
    query = result["suggestions"][0]["query_string"]
    assert "ENTRYTYPE" not in query and "{" not in query
    assert "Attention Is All You Need" in query


def test_source_error_is_disclosed():
    def get_with_s2_broken(url, *args, **kwargs):
        if "semanticscholar" in url:
            raise ConnectionError("network down")
        return offline_requests_get(url, *args, **kwargs)

    with patch.multiple("onecite.pipeline.requests", get=get_with_s2_broken):
        result = suggest_references(
            input_content="Attention is all you need, Vaswani et al., NIPS 2017",
            input_type="txt",
        )

    suggestion = result["suggestions"][0]
    sources = {item["source"]: item for item in suggestion["sources"]}
    assert sources["semantic_scholar"]["status"] == "error"
    assert suggestion["status"].endswith("_incomplete")
