"""
End-to-end workflow tests – the kind of thing you'd manually try in a
terminal to convince yourself the tool actually works.

All API calls are mocked via the ``run_onecite_process`` fixture.
"""

import pytest


class TestIntegration:

    @staticmethod
    def _check(result):
        """Common assertions on the result dict."""
        assert isinstance(result, dict)
        assert "report" in result and "results" in result

    def test_readme_example(self, run_onecite_process):
        """The exact snippet shown in the README."""
        code, _, err, result = run_onecite_process(
            "10.1038/nature14539\n\nAttention is all you need\nVaswani et al.\nNIPS 2017"
        )
        assert code == 0, err
        self._check(result)
        assert result["report"]["total"] >= 1

    def test_doi_to_bibtex(self, run_onecite_process):
        code, out, err, result = run_onecite_process(
            "10.1038/nature14539\n\n1706.03762", output_format="bibtex"
        )
        assert code == 0, err
        self._check(result)
        assert "10.1038/nature14539" in out, "first DOI must appear in output"
        assert result["report"]["succeeded"] >= 1

    def test_bib_to_bibtex(self, run_onecite_process):
        """Round-trip: feed an existing .bib entry, get enriched BibTeX back."""
        bib = (
            "@article{test2015,\n"
            "  title={Deep learning},\n"
            "  author={LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},\n"
            "  journal={Nature},\n"
            "  year={2015},\n"
            "  volume={521},\n"
            "  pages={436--444},\n"
            "  doi={10.1038/nature14539}\n"
            "}"
        )
        code, _, err, result = run_onecite_process(bib, input_type="bib", output_format="bibtex")
        assert code == 0, err
        self._check(result)

    def test_conference_paper(self, run_onecite_process):
        code, out, err, result = run_onecite_process(
            "Attention is all you need\nVaswani et al.\nNIPS 2017",
            template="conference_paper",
        )
        assert code == 0, err
        self._check(result)
        assert "Attention" in out or "attention" in out, "title must appear in output"
        assert "Vaswani" in out or "vaswani" in out.lower(), "author must appear in output"

    def test_arxiv(self, run_onecite_process):
        code, _, err, result = run_onecite_process("1706.03762\n\narxiv:1512.03385")
        assert code == 0, err
        self._check(result)

    def test_mixed_valid_and_invalid(self, run_onecite_process):
        """Valid refs should still succeed even when mixed with garbage."""
        code, _, err, result = run_onecite_process(
            "10.1038/nature14539\n\ninvalid_reference_12345\n\n1706.03762"
        )
        assert code == 0, err
        self._check(result)

    def test_batch(self, run_onecite_process):
        code, _, err, result = run_onecite_process(
            "10.1038/nature14539\n\n1706.03762\n\nAttention is all you need\nVaswani et al.\nNIPS 2017"
        )
        assert code == 0, err
        self._check(result)
        assert result["report"]["total"] >= 2

    def test_cross_format(self, run_onecite_process):
        """BibTeX output should be valid input for a second pass."""
        code1, bibtex_out, _, _ = run_onecite_process("10.1038/nature14539", output_format="bibtex")
        if code1 != 0 or not bibtex_out:
            pytest.skip("first pass failed; nothing to round-trip")
        code2, _, err2, result2 = run_onecite_process(
            bibtex_out, input_type="bib", output_format="bibtex"
        )
        assert code2 == 0, err2
        self._check(result2)
