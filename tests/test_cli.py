"""
Test command line interface functionality
Test CLI functionality based on README declarations
"""
import argparse
import pytest
import subprocess
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import onecite.cli as cli
from onecite.exceptions import OneCiteError

class TestCLI:
    """Command line interface tests"""

    def run_onecite_command(self, args, cwd=None):
        """Helper method to run onecite command"""
        cmd = ["onecite"] + args
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "onecite command not found"

    def test_help_command(self):
        """Test --help command"""
        code, stdout, stderr = self.run_onecite_command(["--help"])
        assert code == 0, f"Help command failed: {stderr}"
        assert "Universal citation management" in stdout
        assert "process" in stdout

    def test_version_command(self):
        """Test --version command"""
        code, stdout, stderr = self.run_onecite_command(["--version"])
        assert code == 0, f"Version command failed: {stderr}"
        assert "onecite" in stdout.lower()

    def test_process_help(self):
        """Test process subcommand help"""
        code, stdout, stderr = self.run_onecite_command(["process", "--help"])
        assert code == 0, f"Process help failed: {stderr}"
        
        # Check all options mentioned in README
        expected_options = [
            "--input-type", "--output-format", "--template", 
            "--interactive", "--quiet", "--output"
        ]
        for option in expected_options:
            assert option in stdout, f"Missing CLI option: {option}"

    def test_input_type_choices(self):
        """Test input type choices"""
        code, stdout, stderr = self.run_onecite_command(["process", "--help"])
        assert "{txt,bib}" in stdout, "Input type choices not found"

    def test_output_format_choices(self):
        """Test output format choices"""
        code, stdout, stderr = self.run_onecite_command(["process", "--help"])
        assert "{bibtex,apa,mla}" in stdout, "Output format choices not found"

    def test_invalid_file_error(self):
        """Test invalid file error handling"""
        code, stdout, stderr = self.run_onecite_command(["process", "nonexistent_file.txt"])
        assert code != 0, "Should return error for nonexistent file"

    def test_invalid_output_format_error(self, create_test_file, sample_references):
        """Test invalid output format error handling"""
        test_file = create_test_file(sample_references["doi_only"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--output-format", "invalid"
        ])
        assert code != 0, "Should return error for invalid output format"


class TestCLIUnit:
    def test_process_command_missing_input_file(self, capsys):
        args = argparse.Namespace(
            command="process",
            input_file="definitely_not_exists.txt",
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=None,
            interactive=False,
            quiet=False,
        )

        code = cli.process_command(args)
        captured = capsys.readouterr()
        assert code == 1
        assert "Input file not found" in captured.err

    def test_process_command_quiet_and_output_file(self, tmp_path, capsys):
        input_file = tmp_path / "in.txt"
        input_file.write_text("10.1038/nature14539", encoding="utf-8")
        output_file = tmp_path / "out.txt"

        args = argparse.Namespace(
            command="process",
            input_file=str(input_file),
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=str(output_file),
            interactive=False,
            quiet=True,
        )

        def fake_process_references(*, input_content, input_type, template_name, output_format, interactive_callback):
            assert input_content
            assert input_type == "txt"
            assert template_name
            assert output_format == "bibtex"
            assert interactive_callback([{"title": "T", "authors": [], "journal": "", "year": 2020, "match_score": 75}]) == -1
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("onecite.cli.process_references", side_effect=fake_process_references):
            code = cli.process_command(args)

        captured = capsys.readouterr()
        assert code == 0
        assert captured.out == ""
        assert output_file.read_text(encoding="utf-8") == "OK"

    def test_process_command_interactive_selection_prints_report(self, tmp_path, capsys):
        input_file = tmp_path / "in.txt"
        input_file.write_text("Some query", encoding="utf-8")

        args = argparse.Namespace(
            command="process",
            input_file=str(input_file),
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=None,
            interactive=True,
            quiet=False,
        )

        def fake_process_references(*, input_content, input_type, template_name, output_format, interactive_callback):
            choice = interactive_callback(
                [
                    {"title": "A", "authors": ["X"], "journal": "J", "year": 2020, "match_score": 75},
                    {"title": "B", "authors": ["Y"], "journal": "J", "year": 2021, "match_score": 74},
                ]
            )
            assert choice == 0
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("builtins.input", return_value="1"), patch("onecite.cli.process_references", side_effect=fake_process_references):
            code = cli.process_command(args)

        captured = capsys.readouterr()
        assert code == 0
        assert "Found multiple possible matches" in captured.out
        assert "Processing Report" in captured.out
        assert "Total entries" in captured.out

    def test_process_command_process_references_exception(self, tmp_path, capsys):
        input_file = tmp_path / "in.txt"
        input_file.write_text("Some query", encoding="utf-8")

        args = argparse.Namespace(
            command="process",
            input_file=str(input_file),
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=None,
            interactive=False,
            quiet=False,
        )

        with patch("onecite.cli.process_references", side_effect=RuntimeError("boom")):
            code = cli.process_command(args)

        captured = capsys.readouterr()
        assert code == 1
        assert "Processing failed" in captured.err

    def test_process_command_interactive_invalid_selection_then_skip(self, tmp_path, capsys):
        input_file = tmp_path / "in.txt"
        input_file.write_text("Some query", encoding="utf-8")

        args = argparse.Namespace(
            command="process",
            input_file=str(input_file),
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=None,
            interactive=True,
            quiet=False,
        )

        def fake_process_references(*, input_content, input_type, template_name, output_format, interactive_callback):
            choice = interactive_callback([
                {"title": "A", "authors": [], "journal": "", "year": 2020, "match_score": 75},
            ])
            assert choice == -1
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("builtins.input", side_effect=["99", "0"]), patch(
            "onecite.cli.process_references", side_effect=fake_process_references
        ):
            code = cli.process_command(args)

        captured = capsys.readouterr()
        assert code == 0
        assert "Invalid selection" in captured.out

    def test_process_command_interactive_keyboardinterrupt_cancels(self, tmp_path, capsys):
        input_file = tmp_path / "in.txt"
        input_file.write_text("Some query", encoding="utf-8")

        args = argparse.Namespace(
            command="process",
            input_file=str(input_file),
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=None,
            interactive=True,
            quiet=False,
        )

        def fake_process_references(*, input_content, input_type, template_name, output_format, interactive_callback):
            assert interactive_callback([
                {"title": "A", "authors": [], "journal": "", "year": 2020, "match_score": 75},
            ]) == -1
            return {"results": ["OK"], "report": {"total": 1, "succeeded": 1, "failed_entries": []}}

        with patch("builtins.input", side_effect=KeyboardInterrupt), patch(
            "onecite.cli.process_references", side_effect=fake_process_references
        ):
            code = cli.process_command(args)

        captured = capsys.readouterr()
        assert code == 0
        assert "Operation cancelled" in captured.out

    def test_process_command_output_saved_message_and_failed_entries_print(self, tmp_path, capsys):
        input_file = tmp_path / "in.txt"
        input_file.write_text("Some query", encoding="utf-8")
        output_file = tmp_path / "out.txt"

        args = argparse.Namespace(
            command="process",
            input_file=str(input_file),
            input_type="txt",
            template="journal_article_full",
            output_format="bibtex",
            output=str(output_file),
            interactive=False,
            quiet=False,
        )

        def fake_process_references(*, input_content, input_type, template_name, output_format, interactive_callback):
            return {
                "results": ["OK"],
                "report": {
                    "total": 2,
                    "succeeded": 1,
                    "failed_entries": [{"id": 2, "error": "bad"}],
                },
            }

        with patch("onecite.cli.process_references", side_effect=fake_process_references):
            code = cli.process_command(args)

        captured = capsys.readouterr()
        assert code == 0
        assert "Results saved to" in captured.out
        assert "Failed entries:" in captured.out
        assert "Entry 2: bad" in captured.out

    def test_main_process_branch(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")

        with patch("onecite.cli.create_parser", return_value=parser), patch("onecite.cli.process_command", return_value=0):
            code = cli.main()

        assert code == 0

    def test_main_help_branch(self):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command=None)

        with patch("onecite.cli.create_parser", return_value=parser):
            code = cli.main()

        assert code == 1
        assert parser.print_help.called

    def test_main_version_branch(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="version")

        with patch("onecite.cli.create_parser", return_value=parser):
            code = cli.main()

        captured = capsys.readouterr()
        assert code == 0
        assert "OneCite version" in captured.out

    def test_main_oneciteerror(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")

        with patch("onecite.cli.create_parser", return_value=parser), patch(
            "onecite.cli.process_command", side_effect=OneCiteError("x")
        ):
            code = cli.main()

        captured = capsys.readouterr()
        assert code == 1
        assert "Error: x" in captured.err

    def test_main_generic_exception(self, capsys):
        parser = Mock()
        parser.parse_args.return_value = argparse.Namespace(command="process")

        with patch("onecite.cli.create_parser", return_value=parser), patch(
            "onecite.cli.process_command", side_effect=RuntimeError("x")
        ):
            code = cli.main()

        captured = capsys.readouterr()
        assert code == 1
        assert "Processing failed" in captured.err

