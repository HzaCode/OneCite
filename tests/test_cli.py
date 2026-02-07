"""
Tests for the ``onecite`` CLI (both subprocess-level and unit-level).

The subprocess tests verify that the installed entry-point works end-to-end;
the unit tests poke at ``cli.process_command`` / ``cli.main`` directly so we
can exercise error branches without spawning a child process every time.
"""
import argparse
import subprocess
import sys

import pytest
from unittest.mock import Mock, patch

import onecite.cli as cli
from onecite.exceptions import OneCiteError


# ---------------------------------------------------------------------------
# Subprocess-level ("does the entry-point actually work?")
# ---------------------------------------------------------------------------

class TestCLI:

    @staticmethod
    def _run(args, cwd=None):
        cmd = [sys.executable, "-m", "onecite.cli"] + args
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "timed out"
        except FileNotFoundError:
            return -1, "", "python not found"

    def test_help(self):
        code, out, _ = self._run(["--help"])
        assert code == 0
        assert "Citation management" in out
        assert "process" in out

    def test_version(self):
        code, out, _ = self._run(["--version"])
        assert code == 0
        assert "onecite" in out.lower()

    def test_process_help_lists_all_options(self):
        """All options documented in the README should appear in --help."""
        code, out, _ = self._run(["process", "--help"])
        assert code == 0
        for opt in ("--input-type", "--output-format", "--template",
                     "--interactive", "--quiet", "--output"):
            assert opt in out, f"{opt} missing from process --help"

    def test_input_type_and_output_format_choices(self):
        """Verify the argparse ``choices`` show up."""
        _, out, _ = self._run(["process", "--help"])
        assert "{txt,bib}" in out
        assert "{bibtex,apa,mla}" in out

    def test_nonexistent_file(self):
        code, _, _ = self._run(["process", "no_such_file.txt"])
        assert code != 0

    def test_invalid_output_format(self, create_test_file, sample_references):
        path = create_test_file(sample_references["doi_only"])
        code, _, _ = self._run(["process", path, "--output-format", "invalid"])
        assert code != 0


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
            interactive=False,
            quiet=False,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    # -- Missing / bad input --------------------------------------------------

    def test_missing_input_file(self, capsys):
        code = cli.process_command(self._ns(input_file="nope.txt"))
        assert code == 1
        assert "Input file not found" in capsys.readouterr().err

    # -- quiet + output file --------------------------------------------------

    def test_quiet_writes_to_file(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("10.1038/nature14539", encoding="utf-8")
        outf = tmp_path / "out.bib"

        def _fake(*, input_content, input_type, template_name,
                  output_format, interactive_callback):
            # quiet mode → callback should auto-skip
            assert interactive_callback(
                [{"title": "T", "authors": [], "journal": "", "year": 2020, "match_score": 75}]
            ) == -1
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(
                input_file=str(inf), output=str(outf), quiet=True,
            ))

        assert code == 0
        assert capsys.readouterr().out == ""
        assert outf.read_text(encoding="utf-8") == "OK"

    # -- interactive branch ---------------------------------------------------

    def test_interactive_selects_first(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(*, input_content, input_type, template_name,
                  output_format, interactive_callback):
            choice = interactive_callback([
                {"title": "A", "authors": ["X"], "journal": "J", "year": 2020, "match_score": 75},
                {"title": "B", "authors": ["Y"], "journal": "J", "year": 2021, "match_score": 74},
            ])
            assert choice == 0
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("builtins.input", return_value="1"), \
             patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file=str(inf), interactive=True))

        out = capsys.readouterr().out
        assert code == 0
        assert "Found multiple possible matches" in out
        assert "Processing Report" in out

    def test_interactive_invalid_then_skip(self, tmp_path, capsys):
        """User types an out-of-range number, then 0 to skip."""
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(*, input_content, input_type, template_name,
                  output_format, interactive_callback):
            choice = interactive_callback([
                {"title": "A", "authors": [], "journal": "", "year": 2020, "match_score": 75},
            ])
            assert choice == -1
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("builtins.input", side_effect=["99", "0"]), \
             patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file=str(inf), interactive=True))

        assert code == 0
        assert "Invalid selection" in capsys.readouterr().out

    def test_interactive_ctrl_c(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        def _fake(*, input_content, input_type, template_name,
                  output_format, interactive_callback):
            assert interactive_callback([
                {"title": "A", "authors": [], "journal": "", "year": 2020, "match_score": 75},
            ]) == -1
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("builtins.input", side_effect=KeyboardInterrupt), \
             patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(input_file=str(inf), interactive=True))

        assert code == 0
        assert "Operation cancelled" in capsys.readouterr().out

    # -- error branches -------------------------------------------------------

    def test_process_references_raises(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")

        with patch("onecite.cli.process_references", side_effect=RuntimeError("boom")):
            code = cli.process_command(self._ns(input_file=str(inf)))

        assert code == 1
        assert "Processing failed" in capsys.readouterr().err

    # -- output file + failed entries -----------------------------------------

    def test_output_saved_message_and_failures(self, tmp_path, capsys):
        inf = tmp_path / "in.txt"
        inf.write_text("query", encoding="utf-8")
        outf = tmp_path / "out.bib"

        def _fake(*, input_content, input_type, template_name,
                  output_format, interactive_callback):
            return {
                "results": ["OK"],
                "report": {"total": 2, "succeeded": 1,
                           "failed_entries": [{"id": 2, "error": "bad"}]},
            }

        with patch("onecite.cli.process_references", side_effect=_fake):
            code = cli.process_command(self._ns(
                input_file=str(inf), output=str(outf),
            ))

        out = capsys.readouterr().out
        assert code == 0
        assert "Results saved to" in out
        assert "Failed entries:" in out
        assert "Entry 2: bad" in out

    # -- main() dispatch ------------------------------------------------------

    def test_main_process(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")
        with patch("onecite.cli.create_parser", return_value=parser), \
             patch("onecite.cli.process_command", return_value=0):
            assert cli.main() == 0

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
        with patch("onecite.cli.create_parser", return_value=parser), \
             patch("onecite.cli.process_command", side_effect=OneCiteError("x")):
            assert cli.main() == 1
        assert "Error: x" in capsys.readouterr().err

    def test_main_unexpected_exception(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")
        with patch("onecite.cli.create_parser", return_value=parser), \
             patch("onecite.cli.process_command", side_effect=RuntimeError("x")):
            assert cli.main() == 1
        assert "Processing failed" in capsys.readouterr().err
