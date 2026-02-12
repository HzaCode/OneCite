"""Input format tests that assert parsing/identification correctness, not only non-crashing."""

from onecite.pipeline import IdentifierModule, ParserModule


class TestInputFormats:

    def test_plain_doi(self, sample_references, run_onecite_process):
        code, out, err, result = run_onecite_process(sample_references["doi_only"], input_type="txt")
        assert code == 0, err
        assert result["report"]["succeeded"] == 1
        assert "10.1038/nature14539" in out
        assert "Human-level control through deep reinforcement learning" in out

    def test_multiline_txt(self, sample_references, run_onecite_process):
        content = f"{sample_references['doi_only']}\n\n{sample_references['conference_paper']}"
        code, out, err, result = run_onecite_process(content, input_type="txt")
        assert code == 0, err
        assert result["report"]["total"] == 2
        assert result["report"]["succeeded"] >= 1
        assert out.count("@") >= 1

    def test_bibtex_input(self, sample_references, run_onecite_process):
        code, out, err, result = run_onecite_process(sample_references["bibtex_entry"], input_type="bib")
        assert code == 0, err
        assert result["report"]["total"] == 1
        # Verifies the BibTeX parser path actually carries original fields through.
        assert "Sample Article" in out
        assert "Smith, John and Doe, Jane" in out

    def test_doi_variants_normalize_to_same_identifier(self):
        parser = ParserModule()

        variants = (
            "10.1038/nature14539",
            "doi:10.1038/nature14539",
            "DOI: 10.1038/nature14539",
            "https://doi.org/10.1038/nature14539",
        )

        for text in variants:
            entries = parser.parse(text, input_type="txt")
            assert len(entries) == 1
            assert entries[0]["doi"] == "10.1038/nature14539"

    def test_arxiv_variants_resolve_to_same_id(self):
        ident = IdentifierModule()
        variants = (
            "1706.03762",
            "arxiv:1706.03762",
            "arXiv:1706.03762",
            "https://arxiv.org/abs/1706.03762",
        )

        for value in variants:
            if value.startswith("http"):
                parsed = ident._extract_arxiv_id_from_url(value)
            else:
                parsed = ident._extract_arxiv_id(value)
            assert parsed == "1706.03762"

    def test_conference_paper(self, sample_references, run_onecite_process):
        code, out, err, result = run_onecite_process(sample_references["conference_paper"], input_type="txt")
        assert code == 0, err
        assert result["report"]["succeeded"] == 1
        assert "Attention Is All You Need" in out

    def test_mixed_content(self, sample_references, run_onecite_process):
        blob = "\n\n".join([
            sample_references["doi_only"],
            sample_references["arxiv_id"],
            sample_references["conference_paper"],
        ])
        code, out, err, result = run_onecite_process(blob, input_type="txt")
        assert code == 0, err
        assert result["report"]["total"] == 3
        assert result["report"]["succeeded"] >= 2
        assert "10.1038/nature14539" in out
        assert "1706.03762" in out
