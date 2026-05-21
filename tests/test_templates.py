"""
Template system tests.

Templates control which BibTeX fields are considered "required" and how
missing fields trigger enrichment.  We only test the two built-in templates
here; users can add custom ones at runtime.
"""

from onecite.core import TemplateLoader


class TestTemplates:

    def test_list_templates_schema(self):
        templates = TemplateLoader().list_templates()
        names = [template["name"] for template in templates]

        assert names == sorted(names)
        assert "journal_article_full" in names

        journal_template = next(
            template for template in templates if template["name"] == "journal_article_full"
        )
        assert set(journal_template) == {
            "name",
            "entry_type",
            "required_fields",
            "optional_fields",
        }
        assert journal_template["entry_type"] == "@article"
        assert journal_template["required_fields"] == [
            "author",
            "title",
            "journal",
            "year",
        ]
        assert "abstract" in journal_template["optional_fields"]

    def test_default_template(self, sample_references, run_onecite_process):
        """journal_article_full is the default when no --template is given."""
        code, out, err, _ = run_onecite_process(sample_references["doi_only"])
        assert code == 0, err
        assert "@article" in out or "@inproceedings" in out

    def test_journal_article_full_fields(self, sample_references, run_onecite_process):
        """Explicitly requesting journal_article_full should fill title/author/year."""
        code, out, err, _ = run_onecite_process(
            sample_references["doi_only"], template="journal_article_full"
        )
        assert code == 0, err
        low = out.lower()
        for f in ("title", "author", "year"):
            assert f in low, f"missing field: {f}"

    def test_conference_paper_template(self, sample_references, run_onecite_process):
        code, _, err, _ = run_onecite_process(
            sample_references["conference_paper"], template="conference_paper"
        )
        assert code == 0, err

    def test_nonexistent_template_handled(self, sample_references, run_onecite_process):
        """Unknown template name → graceful fallback, not a crash."""
        code, _, err, _ = run_onecite_process(
            sample_references["doi_only"], template="nonexistent_template"
        )
        assert code == 0 or "template" in err.lower()

    def test_required_fields_filled(self, sample_references, run_onecite_process):
        """Spot-check that the enrichment pipeline actually fills required fields."""
        code, out, err, _ = run_onecite_process(
            sample_references["doi_only"], template="journal_article_full"
        )
        assert code == 0, err
        low = out.lower()
        for f in ("title", "author", "year"):
            assert f in low, f"required field missing: {f}"

    def test_different_entry_types(self, sample_references, run_onecite_process):
        """Journal article vs. conference paper should both work."""
        c1, _, e1, _ = run_onecite_process(
            sample_references["doi_only"], template="journal_article_full"
        )
        assert c1 == 0, e1

        c2, _, e2, _ = run_onecite_process(
            sample_references["conference_paper"], template="conference_paper"
        )
        assert c2 == 0, e2
