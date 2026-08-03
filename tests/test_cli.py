"""
Tests for the ``onecite`` CLI (both subprocess-level and unit-level).

The subprocess tests verify that the installed entry-point works end-to-end;
the unit tests poke at ``cli.process_command`` / ``cli.main`` directly so we
can exercise error branches without spawning a child process every time.
"""

import argparse
import os
import json
import subprocess
import sys

from unittest.mock import Mock, patch

import onecite.cli as cli
from onecite.exceptions import OneCiteError

# ---------------------------------------------------------------------------
# Subprocess-level ("does the entry-point actually work?")
# ---------------------------------------------------------------------------


def _assert_keys(mapping, expected):
    assert set(mapping) == set(expected)


class TestCLI:

    @staticmethod
    def _run(args, cwd=None):
        cmd = [sys.executable, "-m", "onecite.cli"] + args
        env = {**os.environ, "ONECITE_OFFLINE_FIXTURES": "1"}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30, env=env)
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "timed out"
        except FileNotFoundError:
            return -1, "", "python not found"

    def test_help(self):
        code, out, _ = self._run(["--help"])
        assert code == 0
        assert "Auditable normalization" in out
        assert "process" in out
        assert "benchmark" in out
        assert "doctor" in out
        assert "suggest" in out
        assert "templates" in out

    def test_version(self):
        code, out, _ = self._run(["--version"])
        assert code == 0
        assert "onecite" in out.lower()

    def test_version_subcommand(self):
        code, out, err = self._run(["version"])
        assert code == 0
        assert err == ""
        assert "OneCite version" in out

    def test_process_help_lists_all_options(self):
        """All options documented in the README should appear in --help."""
        code, out, _ = self._run(["process", "--help"])
        assert code == 0
        for opt in (
            "--input-type",
            "--output-format",
            "--template",
            "--quiet",
            "--output",
            "--json",
            "--ndjson",
            "--fail-on-unresolved",
        ):
            assert opt in out, f"{opt} missing from process --help"

    def test_suggest_help_lists_options(self):
        code, out, err = self._run(["suggest", "--help"])
        assert code == 0
        assert err == ""
        assert "--input-type" in out
        assert "--limit" in out
        assert "--json" in out
        assert "--google-scholar" in out

    def test_input_type_and_output_format_choices(self):
        """Verify the argparse ``choices`` show up."""
        _, out, _ = self._run(["process", "--help"])
        assert "{txt,bib}" in out
        assert "bibtex" in out

    def test_nonexistent_file_treated_as_string_input(self):
        """fix #36: non-file argument is treated as inline reference string, not an error."""
        code, out, err = self._run(["process", "no_such_file.txt", "--quiet"])
        assert code in (0, 1)

    def test_invalid_output_format(self, create_test_file, sample_references):
        path = create_test_file(sample_references["doi_only"])
        code, _, _ = self._run(["process", path, "--output-format", "invalid"])
        assert code != 0

    def test_unknown_template_is_rejected_not_silently_defaulted(
        self, create_test_file, sample_references
    ):
        # A typo in --template must not silently fall back to the default
        # preset — that would misrepresent which template shaped the output.
        path = create_test_file(sample_references["doi_only"])
        code, _, err = self._run(["process", path, "--template", "journal_article_fulll"])
        assert code != 0
        assert "invalid choice" in err
        assert "journal_article_full" in err  # valid choices are listed

    def test_templates_command(self):
        code, out, err = self._run(["templates"])
        assert code == 0
        assert err == ""
        assert "Available templates:" in out
        assert "journal_article_full" in out
        assert "@article" in out

    def test_templates_command_json(self):
        code, out, err = self._run(["templates", "--json"])
        assert code == 0
        assert err == ""
        data = json.loads(out)
        names = {item["name"] for item in data}
        assert "journal_article_full" in names
        assert all(
            set(item)
            == {
                "name",
                "entry_type",
                "required_fields",
                "optional_fields",
            }
            for item in data
        )

    def test_benchmark_help(self):
        code, out, err = self._run(["benchmark", "--help"])
        assert code == 0
        assert err == ""
        assert "--min-success-rate" in out
        assert "--json" in out
        assert "--live" in out

    def test_doctor_help(self):
        code, out, err = self._run(["doctor", "--help"])
        assert code == 0
        assert err == ""
        assert "--json" in out

    def test_doctor_json_success(self):
        code, out, err = self._run(["doctor", "--json"])
        assert code == 0
        assert err == ""
        data = json.loads(out)
        _assert_keys(
            data,
            {
                "schema_version",
                "tool",
                "command",
                "status",
                "environment",
                "summary",
                "checks",
            },
        )
        _assert_keys(data["environment"], {"python", "executable", "platform", "package_version"})
        _assert_keys(data["summary"], {"total", "passed", "failed"})
        for check in data["checks"]:
            _assert_keys(check, {"name", "status", "message", "details"})
        assert data["schema_version"] == "1.0"
        assert data["command"] == "doctor"
        assert data["status"] == "passed"
        assert {check["name"] for check in data["checks"]} >= {
            "package_version",
            "templates",
            "benchmark_resources",
            "skill_package",
            "offline_benchmark_gate",
        }

    def test_benchmark_gate_uses_unrounded_success_ratio(self, tmp_path):
        suite_path = tmp_path / "rounding-suite.json"
        suite_path.write_text(
            json.dumps(
                {
                    "suite": "rounding-regression",
                    "version": "1.0",
                    "cases": [
                        {
                            "id": "dqn-pass",
                            "input": "10.1038/nature14236",
                            "input_type": "txt",
                            "template": "journal_article_full",
                            "output_format": "bibtex",
                            "expect": {
                                "min_total": 1,
                                "required_substrings": [
                                    "Human-level control through deep reinforcement learning"
                                ],
                            },
                        },
                        {
                            "id": "transformer-pass",
                            "input": "1706.03762",
                            "input_type": "txt",
                            "template": "journal_article_full",
                            "output_format": "bibtex",
                            "expect": {
                                "min_total": 1,
                                "required_substrings": ["Attention Is All You Need"],
                            },
                        },
                        {
                            "id": "sentinel-fail",
                            "input": "10.1038/nature14236",
                            "input_type": "txt",
                            "template": "journal_article_full",
                            "output_format": "bibtex",
                            "expect": {
                                "min_total": 1,
                                "required_substrings": ["missing benchmark sentinel"],
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        code, out, err = self._run(
            [
                "benchmark",
                "--cases",
                str(suite_path),
                "--min-success-rate",
                "0.6667",
                "--json",
            ]
        )

        data = json.loads(out)
        assert code == 1
        assert err == ""
        assert data["status"] == "failed"
        assert data["summary"]["passed"] == 2
        assert data["summary"]["total_cases"] == 3
        assert data["summary"]["success_rate"] == 0.6667

    def test_process_json_hard_failure_is_machine_readable(self, tmp_path):
        bad_input = tmp_path / "not-a-file"
        bad_input.mkdir()

        code, out, err = self._run(["process", str(bad_input), "--json"])

        data = json.loads(out)
        assert code == 1
        assert err == ""
        assert data["status"] == "failed"
        assert data["summary"] == {
            "total": 1,
            "succeeded": 0,
            "failed": 1,
            "success_rate": 0.0,
        }
        assert data["failed_entries"][0]["error"]
        assert data["results"] == []

    def test_process_ndjson_hard_failure_is_machine_readable(self, tmp_path):
        bad_input = tmp_path / "not-a-file"
        bad_input.mkdir()

        code, out, err = self._run(["process", str(bad_input), "--ndjson"])

        lines = [json.loads(line) for line in out.splitlines()]
        assert code == 1
        assert err == ""
        assert [line["type"] for line in lines] == ["summary", "failure"]
        assert lines[0]["status"] == "failed"
        assert lines[1]["entry"]["error"]

    def test_suggest_json_subprocess_envelope_has_no_passed_status(self):
        code, out, err = self._run(
            [
                "suggest",
                "Attention is all you need, Vaswani et al., NIPS 2017",
                "--json",
            ]
        )

        data = json.loads(out)
        assert code == 0
        assert err == ""
        assert data["command"] == "suggest"
        assert data["status"] == "completed"
        assert "passed" not in out
        assert data["summary"]["total"] == 1
        assert data["suggestions"][0]["candidates"]


# ---------------------------------------------------------------------------
# Unit-level (no subprocess, just call process_command / main directly)
# ---------------------------------------------------------------------------


class TestCLIUnit:

    @staticmethod
    def _ns(**overrides):
        """Build a Namespace with sensible defaults – saves a lot of typing."""
        defaults = dict(
            command="process",
            input_file="placeholder.txt",
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=None,
            quiet=False,
            as_json=False,
            as_ndjson=False,
            fail_on_unresolved=False,
            google_scholar=False,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    # -- Missing / bad input --------------------------------------------------

    def test_bib_file_auto_detected(self, tmp_path, capsys):
        """fix #9: .bib extension should auto-set input_type to 'bib'."""
        inf = tmp_path / "refs.bib"
        inf.write_text("@article{A, title={T}}", encoding="utf-8")
        captured = {}

        def _fake(*, input_type, **kw):
            captured["input_type"] = input_type
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("onecite.cli.process_references", side_effect=_fake):
            cli.process_command(self._ns(input_file=str(inf), quiet=True))

        assert captured["input_type"] == "bib"

    def test_string_input_passed_directly(self, capsys):
        """fix #36: non-file argument is treated as inline reference content."""
        captured = {}

        def _fake(*, input_content, **kw):
            captured["content"] = input_content
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file="10.1038/nature14539", quiet=True))

        assert code == 0
        assert captured["content"] == "10.1038/nature14539"

    def test_stdin_input(self, capsys, monkeypatch):
        """fix #36: '-' reads from stdin."""
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("10.1038/nature14539\n"))
        captured = {}

        def _fake(*, input_content, **kw):
            captured["content"] = input_content
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file="-", quiet=True))

        assert code == 0
        assert "10.1038/nature14539" in captured["content"]

    # -- quiet + output file --------------------------------------------------

    def test_quiet_writes_to_file(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("10.1038/nature14539", encoding="utf-8")
        outf = tmp_path / "out.bib"

        def _fake(*, input_content, input_type, template_name, output_format, **kw):
            # process is strictly non-interactive: the CLI must not wire any
            # candidate-selection callback into the pipeline.
            assert "interactive_callback" not in kw
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(
                self._ns(
                    input_file=str(inf),
                    output=str(outf),
                    quiet=True,
                )
            )

        assert code == 0
        assert capsys.readouterr().out == ""
        assert outf.read_text(encoding="utf-8") == "OK"

    # -- error branches -------------------------------------------------------

    def test_process_references_raises(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        with patch("onecite.cli.process_references", side_effect=RuntimeError("boom")):
            code = cli.process_command(self._ns(input_file=str(inf)))

        assert code == 1
        assert "Processing failed" in capsys.readouterr().err

    def test_process_json_output(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(*, input_content, input_type, template_name, output_format, **kw):
            return {
                "results": ["@article{ok}"],
                "report": {
                    "total": 2,
                    "succeeded": 1,
                    "failed_entries": [{"id": 2, "error": "not found"}],
                },
            }

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file=str(inf), as_json=True))

        data = json.loads(capsys.readouterr().out)
        assert code == 0
        _assert_keys(
            data,
            {
                "schema_version",
                "tool",
                "command",
                "status",
                "summary",
                "options",
                "failed_entries",
                "warnings",
                "duplicates",
                "results",
            },
        )
        _assert_keys(
            data["summary"], {"total", "succeeded", "failed", "duplicates", "success_rate"}
        )
        _assert_keys(
            data["options"],
            {
                "input_type",
                "template",
                "output_format",
                "fail_on_unresolved",
            },
        )
        assert data["schema_version"] == "1.0"
        assert data["status"] == "failed"
        assert data["summary"]["failed"] == 1
        assert data["results"] == ["@article{ok}"]

    def test_process_ndjson_output(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(**_kw):
            return {
                "results": ["@article{ok}"],
                "report": {"total": 1, "succeeded": 1, "failed_entries": []},
            }

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file=str(inf), as_ndjson=True))

        lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert code == 0
        assert [line["type"] for line in lines] == ["summary", "result"]
        _assert_keys(
            lines[0],
            {
                "type",
                "schema_version",
                "tool",
                "command",
                "status",
                "summary",
                "options",
            },
        )
        _assert_keys(lines[1], {"type", "index", "content"})
        assert lines[0]["status"] == "passed"
        assert lines[1]["content"] == "@article{ok}"

    def test_process_fail_on_unresolved_exit_code(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(**_kw):
            return {
                "results": [],
                "report": {
                    "total": 1,
                    "succeeded": 0,
                    "failed_entries": [{"id": 1, "error": "not found"}],
                },
            }

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(
                self._ns(
                    input_file=str(inf),
                    as_json=True,
                    fail_on_unresolved=True,
                )
            )

        assert code == 2
        assert json.loads(capsys.readouterr().out)["summary"]["failed"] == 1

    def test_suggest_json_output(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(**_kw):
            return {
                "suggestions": [
                    {
                        "id": 0,
                        "raw_text": "query",
                        "query_string": "query",
                        "status": "candidates_found",
                        "candidates": [
                            {
                                "source": "crossref",
                                "title": "Candidate",
                                "doi": "10.1/candidate",
                                "match_score": 91,
                            }
                        ],
                    }
                ],
                "report": {
                    "total": 1,
                    "with_candidates": 1,
                    "without_candidates": 0,
                },
            }

        with patch("onecite.cli.suggest_references", side_effect=_fake):
            code = cli.suggest_command(
                self._ns(
                    command="suggest",
                    input_file=str(inf),
                    as_json=True,
                    limit=5,
                )
            )

        data = json.loads(capsys.readouterr().out)
        assert code == 0
        _assert_keys(
            data,
            {
                "schema_version",
                "tool",
                "command",
                "status",
                "summary",
                "options",
                "suggestions",
            },
        )
        assert data["status"] == "completed"
        assert data["summary"]["with_candidates"] == 1
        assert data["suggestions"][0]["candidates"][0]["doi"] == "10.1/candidate"

    def test_process_json_output_file_status_uses_stderr(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")
        outf = tmp_path / "out.json"

        def _fake(**_kw):
            return {
                "results": ["@article{ok}"],
                "report": {"total": 1, "succeeded": 1, "failed_entries": []},
            }

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(
                self._ns(
                    input_file=str(inf),
                    output=str(outf),
                    as_json=True,
                )
            )

        captured = capsys.readouterr()
        assert code == 0
        assert captured.out == ""
        assert "Results saved to" in captured.err
        assert json.loads(outf.read_text(encoding="utf-8"))["status"] == "passed"

    # -- output file + failed entries -----------------------------------------

    def test_output_saved_message_and_failures(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")
        outf = tmp_path / "out.bib"

        def _fake(*, input_content, input_type, template_name, output_format, **kw):
            return {
                "results": ["OK"],
                "report": {
                    "total": 2,
                    "succeeded": 1,
                    "failed_entries": [{"id": 2, "error": "bad"}],
                },
            }

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(
                self._ns(
                    input_file=str(inf),
                    output=str(outf),
                )
            )

        out = capsys.readouterr().out
        assert code == 0
        assert "Results saved to" in out
        assert "Failed entries:" in out
        assert "Entry 2: bad" in out

    # -- main() dispatch ------------------------------------------------------

    def test_main_process(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")
        with (
            patch("onecite.cli.create_parser", return_value=parser),
            patch("onecite.cli.process_command", return_value=0),
        ):
            assert cli.main() == 0

    def test_main_templates(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="templates")
        with (
            patch("onecite.cli.create_parser", return_value=parser),
            patch("onecite.cli.templates_command", return_value=0),
        ):
            assert cli.main() == 0

    def test_main_benchmark(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="benchmark")
        with (
            patch("onecite.cli.create_parser", return_value=parser),
            patch("onecite.cli.benchmark_command", return_value=0),
        ):
            assert cli.main() == 0

    def test_main_doctor(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="doctor")
        with (
            patch("onecite.cli.create_parser", return_value=parser),
            patch("onecite.cli.doctor_command", return_value=0),
        ):
            assert cli.main() == 0

    def test_benchmark_command_json_success(self, capsys):
        report = {
            "schema_version": "1.0",
            "suite": "suite",
            "suite_version": "1.0",
            "source_mode": "offline",
            "status": "passed",
            "summary": {
                "total_cases": 1,
                "passed": 1,
                "failed": 0,
                "success_rate": 1.0,
                "min_success_rate": 1.0,
            },
            "cases": [
                {
                    "id": "case",
                    "description": "",
                    "status": "passed",
                    "failures": [],
                    "observed": {"total": 1, "succeeded": 1, "failed": 0},
                }
            ],
        }
        with patch("onecite.cli.run_benchmark", return_value=report):
            code = cli.benchmark_command(
                argparse.Namespace(
                    cases=None,
                    min_success_rate=1.0,
                    as_json=True,
                    live=False,
                )
            )

        data = json.loads(capsys.readouterr().out)
        assert code == 0
        _assert_keys(
            data,
            {
                "schema_version",
                "suite",
                "suite_version",
                "source_mode",
                "status",
                "summary",
                "cases",
            },
        )
        _assert_keys(
            data["summary"],
            {"total_cases", "passed", "failed", "success_rate", "min_success_rate"},
        )
        _assert_keys(data["cases"][0], {"id", "description", "status", "failures", "observed"})
        assert data["status"] == "passed"

    def test_benchmark_command_text_failure(self, capsys):
        report = {
            "suite": "suite",
            "suite_version": "1.0",
            "status": "failed",
            "summary": {
                "total_cases": 1,
                "passed": 0,
                "failed": 1,
                "success_rate": 0.0,
                "min_success_rate": 1.0,
            },
            "cases": [
                {
                    "id": "case",
                    "status": "failed",
                    "failures": ["missing"],
                }
            ],
        }
        with patch("onecite.cli.run_benchmark", return_value=report):
            code = cli.benchmark_command(
                argparse.Namespace(
                    cases=None,
                    min_success_rate=1.0,
                    as_json=False,
                    live=False,
                )
            )

        assert code == 1
        assert "case: failed" in capsys.readouterr().out

    def test_doctor_command_json_failure(self, capsys):
        report = {
            "schema_version": "1.0",
            "tool": "onecite",
            "command": "doctor",
            "status": "failed",
            "environment": {"package_version": "0.0"},
            "summary": {"total": 1, "passed": 0, "failed": 1},
            "checks": [
                {
                    "name": "offline_benchmark_gate",
                    "status": "failed",
                    "message": "benchmark failed",
                    "details": {},
                }
            ],
        }
        with patch("onecite.cli._build_doctor_report", return_value=report):
            code = cli.doctor_command(argparse.Namespace(as_json=True))

        assert code == 1
        assert json.loads(capsys.readouterr().out)["status"] == "failed"

    def test_doctor_command_text_success(self, capsys):
        report = {
            "schema_version": "1.0",
            "tool": "onecite",
            "command": "doctor",
            "status": "passed",
            "environment": {"package_version": "0.1.1"},
            "summary": {"total": 1, "passed": 1, "failed": 0},
            "checks": [
                {
                    "name": "templates",
                    "status": "passed",
                    "message": "ok",
                    "details": {},
                }
            ],
        }
        with patch("onecite.cli._build_doctor_report", return_value=report):
            code = cli.doctor_command(argparse.Namespace(as_json=False))

        assert code == 0
        assert "OneCite doctor: passed" in capsys.readouterr().out

    def test_main_no_command(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command=None)
        with patch("onecite.cli.create_parser", return_value=parser):
            assert cli.main() == 1
        assert parser.print_help.called

    def test_main_version(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="version")
        with patch("onecite.cli.create_parser", return_value=parser):
            assert cli.main() == 0
        assert "OneCite version" in capsys.readouterr().out

    def test_main_onecite_error(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")
        with (
            patch("onecite.cli.create_parser", return_value=parser),
            patch("onecite.cli.process_command", side_effect=OneCiteError("x")),
        ):
            assert cli.main() == 1
        assert "Error: x" in capsys.readouterr().err

    def test_main_unexpected_exception(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")
        with (
            patch("onecite.cli.create_parser", return_value=parser),
            patch("onecite.cli.process_command", side_effect=RuntimeError("x")),
        ):
            assert cli.main() == 1
        assert "Processing failed" in capsys.readouterr().err


class TestOutputWriteFailure:
    """A bad --output path must not discard computed results or misattribute
    the IO failure as a processing failure."""

    def test_results_rescued_to_stdout_on_unwritable_path(self, tmp_path):
        inf = tmp_path / "in.txt"
        inf.write_text("10.1038/nature14236", encoding="utf-8")
        bad_path = tmp_path / "no_such_dir" / "out.bib"

        cmd = [
            sys.executable,
            "-m",
            "onecite.cli",
            "process",
            str(inf),
            "--quiet",
            "-o",
            str(bad_path),
        ]
        env = {**os.environ, "ONECITE_OFFLINE_FIXTURES": "1"}
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)

        assert r.returncode == 1
        assert "could not be written" in r.stderr
        # The computed BibTeX is rescued to stdout, not lost.
        assert "@article" in r.stdout
        assert "Human-level control" in r.stdout
