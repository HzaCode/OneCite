from pathlib import Path


def test_onecite_skill_package_exists():
    skill_path = Path("skills/onecite/SKILL.md")

    assert skill_path.is_file()
    text = skill_path.read_text(encoding="utf-8")
    assert "name: onecite" in text
    assert "onecite process" in text
    assert "onecite benchmark --json" in text
    assert "onecite doctor --json" in text
    assert "OneCite performs deterministic source lookups" in text
    assert "Repository Validation Checks" in text
    assert "Start from the Roadmap section in `README.md`" in text
    assert "ROADMAP.md" not in text
    assert "flake8 onecite tests --statistics --count" in text
    assert "Do not report local verification evidence" in text


def test_roadmap_docs_are_packaged():
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    manifest_text = Path("MANIFEST.in").read_text(encoding="utf-8")
    docs_readme = Path("docs/README.md").read_text(encoding="utf-8")

    assert "docs/benchmarking.rst" in pyproject_text
    assert "docs/cli_contracts.rst" in pyproject_text
    assert "docs/onecite_skill.rst" in pyproject_text
    assert "share/onecite/skills/onecite" in pyproject_text
    assert "skills/onecite/SKILL.md" in pyproject_text
    assert "benchmarks/leaderboard.json" in pyproject_text
    assert '"onecite.templates"' in pyproject_text
    assert '"build>=1.0"' in pyproject_text
    assert 'license = "MIT"' in pyproject_text
    assert 'license-files = ["LICENSE"]' in pyproject_text
    assert "recursive-include docs" in manifest_text
    assert "include skills/onecite/SKILL.md" in manifest_text
    assert "benchmarking.rst" in docs_readme
    assert "cli_contracts.rst" in docs_readme
    assert "onecite_skill.rst" in docs_readme
