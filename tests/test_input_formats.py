"""
Verify that all advertised input formats are accepted and produce output.

Uses the mocked fixture so these are fast + deterministic.
"""


class TestInputFormats:

    def test_plain_doi(self, sample_references, run_onecite_process):
        code, out, err, _ = run_onecite_process(sample_references["doi_only"], input_type="txt")
        assert code == 0, err
        assert "@article" in out or "@inproceedings" in out

    def test_multiline_txt(self, sample_references, run_onecite_process):
        """Two refs separated by a blank line."""
        content = f"{sample_references['doi_only']}\n\n{sample_references['conference_paper']}"
        code, out, err, _ = run_onecite_process(content, input_type="txt")
        assert code == 0, err
        assert out.count("@") >= 1

    def test_bibtex_input(self, sample_references, run_onecite_process):
        code, _, err, _ = run_onecite_process(sample_references["bibtex_entry"], input_type="bib")
        assert code == 0, err

    def test_doi_variants(self, run_onecite_process):
        """All common DOI notations should be recognised."""
        for doi in (
            "10.1038/nature14539",
            "doi:10.1038/nature14539",
            "DOI: 10.1038/nature14539",
            "https://doi.org/10.1038/nature14539",
        ):
            code, out, err, _ = run_onecite_process(doi, input_type="txt")
            assert code == 0, f"failed for {doi!r}: {err}"
            assert out.strip(), f"empty output for {doi!r}"

    def test_arxiv_variants(self, run_onecite_process):
        for arxiv in ("1706.03762", "arxiv:1706.03762", "arXiv:1706.03762",
                       "https://arxiv.org/abs/1706.03762"):
            code, _, err, _ = run_onecite_process(arxiv, input_type="txt")
            assert code == 0, f"failed for {arxiv!r}: {err}"

    def test_conference_paper(self, sample_references, run_onecite_process):
        code, _, err, _ = run_onecite_process(sample_references["conference_paper"], input_type="txt")
        assert code == 0, err

    def test_mixed_content(self, sample_references, run_onecite_process):
        blob = "\n\n".join([
            sample_references["doi_only"],
            sample_references["arxiv_id"],
            sample_references["conference_paper"],
        ])
        code, out, err, _ = run_onecite_process(blob, input_type="txt")
        assert code == 0, err
        assert out.count("@") >= 1
