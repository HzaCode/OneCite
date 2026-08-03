"""
Shared fixtures for the OneCite test suite.

Most tests that hit external APIs (Crossref, arXiv, Semantic Scholar …)
go through the ``run_onecite_process`` fixture which patches
``requests.get`` with our hand-crafted mock responses so the CI stays
deterministic and fast.
"""

import os
import shutil
import tempfile

import pytest
from unittest.mock import patch

from .mock_responses import mock_requests_get

# ---------------------------------------------------------------------------
# Network guard: unit tests must never hit live APIs
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_unmocked_network(request, monkeypatch):
    """Fail loudly on any unmocked in-process network call.

    A test that silently reaches a live API is nondeterministic and slow —
    exactly what this suite promises not to be. Tests either mock/patch
    ``requests.get`` themselves (the patch simply overrides this guard) or
    carry the ``live`` marker to opt out. Subprocess-level CLI tests are
    unaffected (the guard lives in this process only); they run with
    ``ONECITE_OFFLINE_FIXTURES=1``.
    """
    if request.node.get_closest_marker("live"):
        yield
        return

    def _blocked_get(url, *args, **kwargs):
        raise AssertionError(
            f"Unmocked network call from a non-live test: GET {url}. "
            "Patch onecite.pipeline.requests.get (e.g. with the offline "
            "fixtures) or mark the test with @pytest.mark.live."
        )

    monkeypatch.setattr("onecite.pipeline.requests.get", _blocked_get)
    yield


# ---------------------------------------------------------------------------
# Simple scalar fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_doi():
    return "10.1038/nature14539"


@pytest.fixture
def sample_arxiv():
    return "1706.03762"


@pytest.fixture
def sample_text_query():
    return "Attention is all you need, Vaswani et al., NIPS 2017"


@pytest.fixture
def sample_bibtex():
    return """@article{sample2020,
  title={Sample Article},
  author={Smith, John and Doe, Jane},
  journal={Nature},
  year={2020},
  volume={580},
  pages={1-10}
}"""


@pytest.fixture
def sample_references():
    """Dict of canned inputs keyed by type – keeps individual tests short."""
    return {
        "doi_only": "10.1038/nature14539",
        "arxiv_id": "1706.03762",
        "conference_paper": "Attention is all you need\nVaswani et al.\nNIPS 2017",
        "bibtex_entry": (
            "@article{sample2020,\n"
            "  title={Sample Article},\n"
            "  author={Smith, John and Doe, Jane},\n"
            "  journal={Nature},\n"
            "  year={2020},\n"
            "  volume={580},\n"
            "  pages={1-10},\n"
            "  doi={10.1038/nature14539}\n"
            "}"
        ),
    }


# ---------------------------------------------------------------------------
# File / directory helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def create_test_file(tmp_path):
    """Return a factory that writes *content* to a temp file and gives back
    its path as a string (most CLI helpers expect ``str``, not ``Path``)."""

    def _create(content, filename="test_input.txt"):
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _create


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    if os.path.exists(d):
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# High-level "run the whole pipeline" fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def run_onecite_process():
    """Execute ``process_references`` with mocked HTTP so we never touch
    real APIs during normal test runs.

    Returns *(exit_code, stdout_text, stderr_text, raw_result_dict)*.
    """

    def _run(
        input_content,
        input_type="txt",
        template="journal_article_full",
        output_format="bibtex",
    ):
        try:
            with (
                patch("onecite.pipeline.requests.get", side_effect=mock_requests_get),
                patch("onecite.core.requests.get", side_effect=mock_requests_get),
                patch("requests.get", side_effect=mock_requests_get),
            ):
                from onecite import process_references

                result = process_references(
                    input_content=input_content,
                    input_type=input_type,
                    template_name=template,
                    output_format=output_format,
                    interactive_callback=lambda c: 0 if c else -1,
                )
                stdout = "\n\n".join(result["results"])
                return 0, stdout, "", result
        except Exception as exc:
            return 1, "", str(exc), None

    return _run
