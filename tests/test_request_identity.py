"""Regression tests for versioned, contactable outbound request identity."""

from io import BytesIO
from unittest.mock import patch

from onecite import __email__, __version__
from onecite.pipeline import EnricherModule, IdentifierModule

EXPECTED_USER_AGENT = (
    f"OneCite/{__version__} " f"(https://github.com/HzaCode/OneCite; mailto:{__email__})"
)


class DummyResponse:
    """Minimal response used to capture headers without network access."""

    status_code = 404

    def __init__(self):
        self.headers: dict[str, str] = {}
        self.raw = BytesIO(b"")

    def json(self) -> list[object]:
        return []


def test_crossref_request_identity_tracks_package_version_and_contact():
    """Both Crossref clients derive identity from the package metadata."""
    identifier = IdentifierModule()
    enricher = EnricherModule()

    for client in (identifier, enricher):
        assert client._crossref_headers["User-Agent"] == EXPECTED_USER_AGENT
        assert client._crossref_mailto == __email__


def test_github_request_identity_tracks_package_version_and_contact():
    """GitHub repository lookups use the same current, contactable identity."""
    identifier = IdentifierModule()
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs)
        return DummyResponse()

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        assert identifier._extract_github_info("https://github.com/HzaCode/OneCite") is None

    assert captured["headers"]["User-Agent"] == EXPECTED_USER_AGENT


def test_webpage_request_identity_tracks_package_version_and_contact():
    """Generic DOI-page lookups do not fall back to a hard-coded version."""
    identifier = IdentifierModule()
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs)
        return DummyResponse()

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        assert identifier._extract_doi_from_url("https://example.org/work") is None

    assert captured["headers"]["User-Agent"] == EXPECTED_USER_AGENT
