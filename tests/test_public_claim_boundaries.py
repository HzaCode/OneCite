"""Prevent public documentation from regressing into unsupported promises."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CITATION.cff",
    REPO_ROOT / ".zenodo.json",
    *sorted((REPO_ROOT / "docs").rglob("*.rst")),
]


def public_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_PATHS)


def test_public_text_does_not_make_forbidden_product_promises() -> None:
    text = public_text()
    forbidden_patterns = {
        "BibTeX-only support": r"\b(?:only|exclusively)\s+(?:supports?|produces?)\s+BibTeX\b",
        "CSL-JSON unsupported": r"\b(?:does\s+not|doesn't)\s+support\s+CSL[- ]JSON\b",
        "never fabricates": r"\bnever\s+(?:fabricates?|hallucinates?)\b",
        "guaranteed bibliographic truth": (
            r"\bguarantees?\s+(?:citation\s+|bibliographic\s+)?"
            r"(?:accuracy|authenticity|correctness)\b"
        ),
        "verified-citation product claim": r"\bverified\s+(?:citation|citations|reference|references)\b",
    }

    for label, pattern in forbidden_patterns.items():
        assert re.search(pattern, text, flags=re.IGNORECASE) is None, label


def test_public_text_preserves_format_and_truth_boundaries() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    pipeline_docs = (REPO_ROOT / "docs" / "api" / "pipeline.rst").read_text(encoding="utf-8")
    benchmark_docs = (REPO_ROOT / "docs" / "benchmarking.rst").read_text(encoding="utf-8")
    external_docs = (REPO_ROOT / "docs" / "external_services.rst").read_text(encoding="utf-8")
    normalized_pipeline_docs = " ".join(pipeline_docs.split())
    normalized_benchmark_docs = " ".join(benchmark_docs.split())
    normalized_external_docs = " ".join(external_docs.split())

    assert "produces BibTeX or CSL-JSON" in readme
    assert (
        "Source resolution does not establish that a work is authentic, unretracted, "
        "or correctly described by upstream metadata."
    ) in readme
    assert 'neither ``"bibtex"`` nor ``"csl-json"``' in normalized_pipeline_docs
    assert "not a comprehensive citation accuracy benchmark" in normalized_benchmark_docs
    assert (
        "Candidate scores are similarity and ranking signals, not verification"
        in normalized_external_docs
    )
