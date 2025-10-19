"""
Test command line interface functionality
Test CLI functionality based on README declarations
"""
import pytest
import subprocess
import os
import tempfile
from pathlib import Path

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

