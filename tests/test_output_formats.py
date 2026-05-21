"""
Verify the BibTeX output format.

Runs as a subprocess so we also exercise the ``--output`` flag and file I/O.
"""

import os
import subprocess
import sys


def _run(args, cwd=None):
    cmd = [sys.executable, "-m", "onecite.cli"] + args
    env = {**os.environ, "ONECITE_OFFLINE_FIXTURES": "1"}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30, env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"


class TestOutputFormats:

    # -- BibTeX ---------------------------------------------------------------

    def test_bibtex_default(self, create_test_file, sample_references):
        f = create_test_file(sample_references["doi_only"])
        code, out, err = _run(["process", f, "--quiet"])
        assert code == 0, err
        assert "@article" in out or "@inproceedings" in out
        # basic structural sanity
        for field in ("title", "author"):
            assert field in out.lower(), f"missing {field}"
        assert "{" in out and "}" in out

    def test_bibtex_explicit(self, create_test_file, sample_references):
        f = create_test_file(sample_references["doi_only"])
        code, out, err = _run(["process", f, "--output-format", "bibtex", "--quiet"])
        assert code == 0, err
        assert "@" in out

    def test_invalid_format_rejected(self, create_test_file, sample_references):
        """fix #31/#32: apa/mla are no longer supported; CLI should reject them."""
        f = create_test_file(sample_references["doi_only"])
        for fmt in ("apa", "mla"):
            code, _, err = _run(["process", f, "--output-format", fmt, "--quiet"])
            assert code != 0, f"{fmt} should have been rejected by argparse"

    # -- file output ----------------------------------------------------------

    def test_output_to_file(self, create_test_file, sample_references, temp_dir):
        f = create_test_file(sample_references["doi_only"])
        out_path = os.path.join(temp_dir, "output.bib")
        code, _, err = _run(["process", f, "--output", out_path, "--quiet"])
        assert code == 0, err
        assert os.path.exists(out_path), "output file not created"
        with open(out_path, encoding="utf-8") as fh:
            content = fh.read()
        assert "@" in content

    # -- field completeness ---------------------------------------------------

    def test_key_fields_present(self, create_test_file, sample_references):
        """The sample DOI should resolve to an entry with at least these fields."""
        f = create_test_file(sample_references["doi_only"])
        code, out, err = _run(["process", f, "--quiet"])
        assert code == 0, err
        low = out.lower()
        for field in ("title", "author", "journal", "year"):
            assert field in low, f"missing {field}"
