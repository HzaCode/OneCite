"""CSL-JSON output format.

CSL-JSON is the interchange format consumed by pandoc, Quarto, citeproc, and
reference-manager imports. `onecite process --output-format csl-json` must
emit one valid JSON array of CSL items with faithful field mapping — plain
Unicode, no LaTeX escapes. All tests run offline against bundled fixtures.
"""

import json
import os
import subprocess
import sys
from unittest.mock import patch

from onecite import process_references
from onecite.benchmarks.offline import offline_requests_get
from onecite.pipeline.formatter import FormatterModule


def _process(text, output_format="csl-json"):
    with patch.multiple("onecite.pipeline.requests", get=offline_requests_get):
        return process_references(
            input_content=text,
            input_type="txt",
            template_name="journal_article_full",
            output_format=output_format,
        )


def test_api_emits_valid_csl_items():
    result = _process("10.1038/nature14236")
    assert result["report"]["succeeded"] == 1
    item = json.loads(result["results"][0])
    assert item["type"] == "article-journal"
    assert item["title"] == "Human-level control through deep reinforcement learning"
    assert item["DOI"] == "10.1038/nature14236"
    assert item["issued"] == {"date-parts": [[2015]]}
    assert {"family": "Mnih", "given": "Volodymyr"} in item["author"]
    assert item["container-title"] == "Nature"


def test_cli_emits_single_valid_json_array(tmp_path):
    refs = tmp_path / "refs.txt"
    refs.write_text("10.1038/nature14236\n\n10.1038/nature14539\n", encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "onecite.cli",
            "process",
            str(refs),
            "--output-format",
            "csl-json",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "ONECITE_OFFLINE_FIXTURES": "1"},
    )
    assert r.returncode == 0, r.stderr
    items = json.loads(r.stdout)
    assert isinstance(items, list) and len(items) == 2
    assert {item["type"] for item in items} == {"article-journal"}
    assert all("id" in item for item in items)


def test_author_parsing_handles_structured_and_literal_names():
    parse = FormatterModule._parse_bibtex_authors
    assert parse("Mnih, Volodymyr and Silver, David") == [
        {"family": "Mnih", "given": "Volodymyr"},
        {"family": "Silver", "given": "David"},
    ]
    # No comma → literal name, never guessed apart.
    assert parse("DeepMind Technologies") == [{"literal": "DeepMind Technologies"}]
    assert parse("") == []


def test_unicode_stays_plain_not_latex_escaped():
    formatter = FormatterModule()
    entry = {
        "id": 0,
        "doi": "10.1234/x",
        "status": "completed",
        "bib_key": "Kunsch2020",
        "bib_data": {
            "ENTRYTYPE": "article",
            "ID": "Kunsch2020",
            "title": "Über die Wärme",
            "author": "Künsch, Hans",
            "year": "2020",
        },
    }
    result = formatter.format([entry], "csl-json")
    item = json.loads(result["results"][0])
    assert item["title"] == "Über die Wärme"  # no {\"U} LaTeX escapes
    assert item["author"] == [{"family": "Künsch", "given": "Hans"}]


def test_unsupported_format_lists_both_supported():
    formatter = FormatterModule()
    entry = {
        "id": 0,
        "doi": "",
        "status": "completed",
        "bib_key": "k",
        "bib_data": {"ENTRYTYPE": "article", "ID": "k", "title": "T", "author": "A, B"},
    }
    result = formatter.format([entry], "ris")
    # Formatting failures are reported per entry, not raised.
    assert result["report"]["succeeded"] == 0
    error = result["report"]["failed_entries"][0]["error"]
    assert "bibtex" in error and "csl-json" in error


def test_dedup_applies_to_csl_json_too():
    result = _process("10.1038/nature14539\n\n10.1038/nature14539")
    assert len(result["results"]) == 1
    assert len(result["report"]["duplicates"]) == 1


def test_brace_protected_title_is_cleanly_unbraced():
    # str.strip("{}") mangled "{ResNet}: ..." into unbalanced "ResNet}: ...";
    # braces are LaTeX markup with no meaning in CSL and must all go.
    formatter = FormatterModule()
    entry = {
        "id": 0,
        "doi": "10.1234/x",
        "status": "completed",
        "bib_key": "He2016",
        "bib_data": {
            "ENTRYTYPE": "article",
            "ID": "He2016",
            "title": "{ResNet}: Deep Residual Learning",
            "author": "{DeepMind} Technologies and He, Kaiming",
            "year": "2016",
            "pages": "3--14",
        },
    }
    item = json.loads(formatter.format([entry], "csl-json")["results"][0])
    assert item["title"] == "ResNet: Deep Residual Learning"
    assert "{" not in item["title"] and "}" not in item["title"]
    # BibTeX "--" page convention is normalized to plain text.
    assert item["page"] == "3-14"
    assert {"literal": "DeepMind Technologies"} in item["author"]
