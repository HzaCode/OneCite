"""Regression tests for strong-DOI registry response identity checks."""

import copy

from unittest.mock import patch

from onecite.benchmarks.offline import DATACITE_DRYAD_DATASET
from onecite.pipeline import IdentifierModule

from .mock_responses import MOCK_CROSSREF_RESPONSE, MockResponse


def _raw_entry(doi):
    return {
        "id": 0,
        "raw_text": doi,
        "doi": doi,
        "url": None,
        "query_string": None,
    }


def test_crossref_mismatched_response_doi_fails_closed():
    payload = copy.deepcopy(MOCK_CROSSREF_RESPONSE)
    payload["message"]["DOI"] = "10.1038/nature14236"

    with patch(
        "onecite.pipeline.requests.get",
        return_value=MockResponse(json_data=payload),
    ):
        result = IdentifierModule()._identify_single_entry(_raw_entry("10.1038/nature14539"))

    assert result["status"] == "identification_failed"
    assert result["failure_reason"] == "source_error"
    assert result["doi"] is None
    assert result["metadata"] == {}


def test_crossref_matching_normalized_response_doi_succeeds():
    payload = copy.deepcopy(MOCK_CROSSREF_RESPONSE)
    payload["message"]["DOI"] = "https://doi.org/10.1038/NATURE14539"

    with patch(
        "onecite.pipeline.requests.get",
        return_value=MockResponse(json_data=payload),
    ):
        result = IdentifierModule()._identify_single_entry(_raw_entry("10.1038/nature14539"))

    assert result["status"] == "identified"
    assert result["doi"] == "10.1038/nature14539"
    assert result["metadata"]["doi"] == "10.1038/nature14539"


def test_datacite_mismatched_response_doi_fails_closed():
    payload = copy.deepcopy(DATACITE_DRYAD_DATASET)
    payload["data"]["id"] = "10.5061/dryad.different"
    payload["data"]["attributes"]["doi"] = "10.5061/dryad.different"

    with patch(
        "onecite.pipeline.requests.get",
        return_value=MockResponse(json_data=payload),
    ):
        result = IdentifierModule()._query_datacite("10.5061/dryad.8515")

    assert result is None


def test_datacite_matching_normalized_response_doi_succeeds():
    payload = copy.deepcopy(DATACITE_DRYAD_DATASET)
    payload["data"]["id"] = "https://doi.org/10.5061/DRYAD.8515"
    payload["data"]["attributes"]["doi"] = "doi:10.5061/dryad.8515"

    with patch(
        "onecite.pipeline.requests.get",
        return_value=MockResponse(json_data=payload),
    ):
        result = IdentifierModule()._query_datacite("10.5061/dryad.8515")

    assert result is not None
    assert result["doi"] == "10.5061/dryad.8515"
