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
    assert "flake8 src/onecite tests --statistics --count" in text
    assert "Do not report local verification evidence" in text


def test_packaging_ships_consumables_but_not_docs():
    """Installed data-files are limited to artifacts with an actual consumer.

    `onecite doctor` locates SKILL.md and the benchmark baseline under
    sys.prefix/share, so those are installed. Documentation has no installed
    consumer — it belongs in the sdist (via MANIFEST.in) and on the docs
    site, not in every user's sys.prefix.
    """
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    manifest_text = Path("MANIFEST.in").read_text(encoding="utf-8")
    docs_readme = Path("docs/README.md").read_text(encoding="utf-8")
    test_workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")

    # Consumables stay installed…
    assert "share/onecite/skills/onecite" in pyproject_text
    assert "skills/onecite/SKILL.md" in pyproject_text
    assert "benchmarks/leaderboard.json" in pyproject_text
    # …while documentation is not shipped as data-files.
    assert "share/onecite/docs" not in pyproject_text

    assert 'package-dir = {"" = "src"}' in pyproject_text
    assert 'where = ["src"]' in pyproject_text
    assert 'include = ["onecite*"]' in pyproject_text
    assert '"build>=1.0"' in pyproject_text
    assert 'license = "MIT"' in pyproject_text
    assert 'license-files = ["LICENSE"]' in pyproject_text

    # Docs are still part of the source distribution and indexed.
    manifest_lines = manifest_text.splitlines()
    assert "include LICENSE" in manifest_lines
    assert "include Licence.txt" not in manifest_lines
    assert "include LICENSE.txt" not in manifest_lines
    # Repository aliases remain byte-identical, while package configuration
    # names only canonical LICENSE to avoid duplicate license metadata.
    assert "exclude LICENSE.txt" not in manifest_lines
    assert '"LICENSE.txt"' not in pyproject_text
    assert "/Licence\\.txt$" not in test_workflow
    assert "/LICENSE\\.txt$" not in test_workflow
    assert Path("LICENSE").read_bytes() == Path("Licence.txt").read_bytes()
    assert Path("LICENSE").read_bytes() == Path("LICENSE.txt").read_bytes()
    assert "recursive-include src/onecite/templates *.yaml" in manifest_lines
    assert "recursive-include src/onecite/benchmarks *.json *.py" in manifest_lines
    assert any(line.startswith("recursive-include docs") for line in manifest_lines)
    assert "include skills/onecite/SKILL.md" in manifest_lines
    assert "benchmarking.rst" in docs_readme
    assert "cli_contracts.rst" in docs_readme
    assert "onecite_skill.rst" in docs_readme
