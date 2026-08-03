"""Regression tests for fail-closed Zenodo response identity checks."""

from unittest.mock import patch

from onecite.pipeline import IdentifierModule


class ZenodoResponse:
    """Minimal synthetic response; these tests never contact Zenodo."""

    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _record_payload(**overrides):
    payload = {
        "id": 12345,
        "doi": "10.5281/zenodo.12345",
        "metadata": {
            "title": "Synthetic dataset",
            "creators": [{"name": "Example, Ada"}],
            "publication_date": "2024-01-02",
            "resource_type": {"type": "dataset"},
        },
    }
    payload.update(overrides)
    return payload


def _extract(input_doi, payload):
    with patch(
        "onecite.pipeline.requests.get",
        return_value=ZenodoResponse(payload),
    ):
        return IdentifierModule()._extract_zenodo_info(input_doi)


def test_matching_record_id_and_version_doi_succeeds():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(doi="https://doi.org/10.5281/ZENODO.12345"),
    )

    assert info is not None
    assert info["doi"] == "10.5281/zenodo.12345"
    assert info["version_doi"] == "10.5281/zenodo.12345"
    assert info["concept_doi"] is None


def test_matching_record_id_and_concept_doi_relation_succeeds():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(
            id=67890,
            doi="10.5281/zenodo.67890",
            conceptrecid=12345,
            conceptdoi="doi:10.5281/ZENODO.12345",
        ),
    )

    assert info is not None
    assert info["doi"] == "10.5281/zenodo.12345"
    assert info["version_doi"] == "10.5281/zenodo.67890"
    assert info["concept_doi"] == "10.5281/zenodo.12345"
    assert info["record_id"] == "67890"
    assert info["concept_record_id"] == "12345"
    assert info["url"] == "https://zenodo.org/record/67890"


def test_mismatched_response_record_id_fails_closed():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(id=54321),
    )

    assert info is None


def test_mismatched_response_dois_fail_closed():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(
            doi="10.5281/zenodo.67890",
            conceptdoi="10.5281/zenodo.11111",
        ),
    )

    assert info is None


def test_missing_response_version_doi_fails_closed():
    payload = _record_payload(conceptdoi="10.5281/zenodo.12345")
    del payload["doi"]

    assert _extract("10.5281/zenodo.12345", payload) is None


def test_same_version_and_concept_identity_is_ambiguous_and_fails_closed():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(
            conceptrecid=12345,
            conceptdoi="10.5281/zenodo.12345",
        ),
    )

    assert info is None


def test_version_doi_suffix_must_match_response_record_id():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(id=12345, doi="10.5281/zenodo.67890"),
    )

    assert info is None


def test_concept_doi_suffix_must_match_concept_record_id():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(
            id=67890,
            doi="10.5281/zenodo.67890",
            conceptrecid=11111,
            conceptdoi="10.5281/zenodo.12345",
        ),
    )

    assert info is None


def test_partial_concept_identity_fails_closed():
    info = _extract(
        "10.5281/zenodo.12345",
        _record_payload(conceptdoi="10.5281/zenodo.12345"),
    )

    assert info is None


def test_software_resource_type_is_not_relabelled_as_dataset():
    payload = _record_payload()
    payload["metadata"]["resource_type"] = {"type": "software"}

    info = _extract("10.5281/zenodo.12345", payload)

    assert info is not None
    assert info["type"] == "software"
    assert info["is_software"] is True
    assert info["is_dataset"] is False
    assert info["resource_type"] == "software"


def test_official_legacy_doi_id_maps_to_its_record_id():
    payload = _record_payload(
        id=7468,
        doi="10.5281/zenodo.7448",
    )

    with patch(
        "onecite.pipeline.requests.get",
        return_value=ZenodoResponse(payload),
    ) as mock_get:
        info = IdentifierModule()._extract_zenodo_info("10.5281/zenodo.7448")

    assert info is not None
    assert info["doi"] == "10.5281/zenodo.7448"
    assert info["record_id"] == "7468"
    assert info["url"] == "https://zenodo.org/record/7468"
    mock_get.assert_called_once_with("https://zenodo.org/api/records/7468", timeout=10)


def test_wrong_legacy_doi_pair_fails_closed():
    payload = _record_payload(
        id=7468,
        doi="10.5281/zenodo.7449",
    )

    assert _extract("10.5281/zenodo.7448", payload) is None
