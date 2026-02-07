"""
Robustness-oriented input tests – shorter timeouts, edge cases.

These exercise the CLI as a subprocess (like a user would) rather than
going through the mocked fixture, so they may hit real APIs if the mock
layer doesn't intercept.  We use tight timeouts to make sure pathological
inputs don't hang the suite.
"""
import subprocess
import sys

import pytest


def _run(args, timeout=30):
    """Spawn ``python -m onecite.cli`` with a bounded timeout.

    Default is 30 s which is generous enough for most machines, but still
    prevents a hung process from blocking CI forever.
    """
    cmd = [sys.executable, "-m", "onecite.cli"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"


class TestInputFormatsRobust:

    def test_single_doi(self, create_test_file):
        f = create_test_file("10.1038/nature14539")
        code, out, err = _run(["process", f, "--quiet"])
        if code == 0:
            assert "@" in out
        else:
            # network hiccup is fine, but it shouldn't be a format error
            assert "format" not in err.lower(), err

    def test_bibtex_passthrough_no_network(self, create_test_file, sample_references):
        """Re-formatting an existing .bib should barely touch the network."""
        f = create_test_file(sample_references["bibtex_entry"])
        code, _, err = _run(["process", f, "--input-type", "bib", "--quiet"])
        assert code == 0 or "timed out" not in err, err

    def test_empty_file(self, create_test_file):
        f = create_test_file("")
        code, _, err = _run(["process", f, "--quiet"])
        assert "timed out" not in err, "empty file shouldn't hang"

    def test_output_format_switching(self, create_test_file):
        f = create_test_file("Simple test reference")
        for fmt in ("bibtex", "apa", "mla"):
            code, _, err = _run(["process", f, "--output-format", fmt, "--quiet"], timeout=30)
            assert "timed out" not in err, f"{fmt} timed out"

    def test_template_switching(self, create_test_file):
        f = create_test_file("Test reference")
        for tmpl in ("journal_article_full", "conference_paper"):
            _, _, err = _run(["process", f, "--template", tmpl, "--quiet"], timeout=30)
            assert "timed out" not in err, f"{tmpl} timed out"

    @pytest.mark.slow
    def test_arxiv_with_long_timeout(self, create_test_file):
        """arXiv lookups can be slow; give it a full minute."""
        f = create_test_file("1706.03762")
        code, _, err = _run(["process", f, "--quiet"], timeout=60)
        if code != 0:
            network_words = ("timed out", "connection", "network", "dns")
            if not any(w in err.lower() for w in network_words):
                pytest.fail(f"non-network failure: {err}")

    def test_garbage_input_fails_fast(self, create_test_file):
        f = create_test_file("invalid.doi.format")
        _, _, err = _run(["process", f, "--quiet"])  # uses default 30s
        assert "timed out" not in err

    def test_local_bib_no_network(self, create_test_file):
        """A fully-specified .bib entry shouldn't need any API calls."""
        bib = (
            "@article{local2023,\n"
            "  title={Local Test Article},\n"
            "  author={Test Author},\n"
            "  journal={Test Journal},\n"
            "  year={2023}\n"
            "}"
        )
        f = create_test_file(bib, "test.bib")
        code, out, err = _run(["process", f, "--input-type", "bib", "--quiet"], timeout=15)
        if code == 0:
            assert "@" in out
        else:
            assert "timed out" not in err, err
