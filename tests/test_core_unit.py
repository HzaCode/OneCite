import os

import yaml

from onecite.core import TemplateLoader


def test_template_loader_custom_templates_dir_is_used(tmp_path):
    loader = TemplateLoader(templates_dir=str(tmp_path))
    assert os.path.samefile(loader.templates_dir, str(tmp_path))


def test_template_loader_missing_template_returns_default(tmp_path):
    loader = TemplateLoader(templates_dir=str(tmp_path))
    template = loader.load_template("does_not_exist")
    assert template["name"] == "journal_article_full"
    assert "fields" in template


def test_template_loader_yaml_error_returns_default(tmp_path, monkeypatch):
    # Create a template file that exists
    (tmp_path / "broken.yaml").write_text("name: [unterminated", encoding="utf-8")

    loader = TemplateLoader(templates_dir=str(tmp_path))

    # Force yaml.safe_load to raise to hit the exception branch
    def raise_yaml(_stream):
        raise yaml.YAMLError("bad")

    monkeypatch.setattr(yaml, "safe_load", raise_yaml)

    template = loader.load_template("broken")
    assert template["name"] == "journal_article_full"
