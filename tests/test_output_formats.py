"""
Verify the three output formats (BibTeX / APA / MLA).

Runs as a subprocess so we also exercise the ``--output`` flag and file I/O.
"""
import os
import subprocess
import sys


def _run(args, cwd=None):
    cmd = [sys.executable, "-m", "onecite.cli"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
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

    # -- APA ------------------------------------------------------------------

    def test_apa(self, create_test_file, sample_references):
        f = create_test_file(sample_references["doi_only"])
        code, out, err = _run(["process", f, "--output-format", "apa", "--quiet"])
        assert code == 0, err
        assert out.strip(), "APA output was empty"

    # -- MLA ------------------------------------------------------------------

    def test_mla(self, create_test_file, sample_references):
        f = create_test_file(sample_references["doi_only"])
        code, out, err = _run(["process", f, "--output-format", "mla", "--quiet"])
        assert code == 0, err
        assert out.strip(), "MLA output was empty"

    # -- cross-format consistency ---------------------------------------------

    def test_all_formats_produce_output(self, create_test_file, sample_references):
        f = create_test_file(sample_references["doi_only"])
        for fmt in ("bibtex", "apa", "mla"):
            code, out, err = _run(["process", f, "--output-format", fmt, "--quiet"])
            assert code == 0, f"{fmt}: {err}"
            assert out.strip(), f"{fmt} produced no output"

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
        """The DQN DOI should resolve to an entry with at least these fields."""
        f = create_test_file(sample_references["doi_only"])
        code, out, err = _run(["process", f, "--quiet"])
        assert code == 0, err
        low = out.lower()
        for field in ("title", "author", "journal", "year"):
            assert field in low, f"missing {field}"
