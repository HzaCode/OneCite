"""Keep privacy/external-service documentation aligned with live routes."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DISCLOSURE_PATH = REPO_ROOT / "docs" / "external_services.rst"
INDEX_PATH = REPO_ROOT / "docs" / "index.rst"
ROUTE_PATHS = [
    REPO_ROOT / "src" / "onecite" / "pipeline" / "identifier.py",
    REPO_ROOT / "src" / "onecite" / "pipeline" / "enricher.py",
]


def test_every_implemented_external_service_is_disclosed() -> None:
    """Every provider endpoint in the pipeline has a named disclosure."""
    route_text = "\n".join(path.read_text(encoding="utf-8") for path in ROUTE_PATHS)
    disclosure = DISCLOSURE_PATH.read_text(encoding="utf-8")

    endpoint_to_disclosure = {
        "api.crossref.org": "Crossref",
        "eutils.ncbi.nlm.nih.gov": "NCBI E-utilities",
        "export.arxiv.org": "arXiv",
        "api.datacite.org": "DataCite",
        "api.semanticscholar.org": "Semantic Scholar",
        "www.googleapis.com/books": "Google Books",
        "api.github.com": "GitHub REST API",
        "zenodo.org/api/records": "Zenodo",
        "api.openaire.eu": "OpenAIRE",
        "api.base-search.net": "BASE",
    }

    for endpoint, provider_name in endpoint_to_disclosure.items():
        assert endpoint in route_text, f"expected implemented endpoint {endpoint}"
        assert provider_name in disclosure, f"missing disclosure for {provider_name}"


def test_disclosure_preserves_high_risk_boundaries() -> None:
    """Regression/smoke checks must not be mistaken for privacy or accuracy proof."""
    disclosure = DISCLOSURE_PATH.read_text(encoding="utf-8")
    normalized_disclosure = " ".join(disclosure.split())

    required_boundaries = [
        "confidential, embargoed, or personally identifying text",
        "validate or allow-list URLs",
        "reads at most 5 MiB",
        "Google Scholar is off by default",
        "does not prove that the work is authentic",
        "Candidate scores are similarity and ranking signals, not verification",
        "does not establish current service availability",
        "do not have a persistent OneCite HTTP-response cache",
    ]
    for boundary in required_boundaries:
        assert boundary in normalized_disclosure


def test_disclosure_is_linked_from_public_documentation() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")
    assert "external_services" in index
