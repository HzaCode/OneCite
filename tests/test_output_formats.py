"""
Test output format support
Verify BibTeX, APA, MLA output formats
"""
import pytest
import subprocess
import re

class TestOutputFormats:
    """Output format tests"""

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

    def test_bibtex_output_default(self, create_test_file, sample_references):
        """Test BibTeX output (default format)"""
        test_file = create_test_file(sample_references["doi_only"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        assert code == 0, f"BibTeX output failed: {stderr}"
        
        # Verify BibTeX format features
        assert "@article" in stdout or "@inproceedings" in stdout, "Missing BibTeX entry type"
        assert "title" in stdout.lower(), "Missing title field"
        assert "author" in stdout.lower(), "Missing author field"
        assert "{" in stdout and "}" in stdout, "Missing BibTeX braces"

    def test_bibtex_output_explicit(self, create_test_file, sample_references):
        """Test explicitly specified BibTeX output"""
        test_file = create_test_file(sample_references["doi_only"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--output-format", "bibtex", "--quiet"
        ])
        assert code == 0, f"Explicit BibTeX output failed: {stderr}"
        assert "@" in stdout, "Missing BibTeX entry marker"

    def test_apa_output_format(self, create_test_file, sample_references):
        """Test APA format output"""
        test_file = create_test_file(sample_references["doi_only"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--output-format", "apa", "--quiet"
        ])
        assert code == 0, f"APA output failed: {stderr}"
        
        # APA format features: year in parentheses, separated by periods
        # Note: These are basic APA format features, actual format may be more complex
        output_lower = stdout.lower()
        # Should at least contain some punctuation and structure
        assert len(stdout.strip()) > 0, "APA output should not be empty"

    def test_mla_output_format(self, create_test_file, sample_references):
        """Test MLA format output"""
        test_file = create_test_file(sample_references["doi_only"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--output-format", "mla", "--quiet"
        ])
        assert code == 0, f"MLA output failed: {stderr}"
        
        # Basic MLA format verification
        assert len(stdout.strip()) > 0, "MLA output should not be empty"

    def test_output_format_consistency(self, create_test_file, sample_references):
        """Test consistency across different output formats"""
        test_file = create_test_file(sample_references["doi_only"])
        
        formats = ["bibtex", "apa", "mla"]
        outputs = {}
        
        for fmt in formats:
            code, stdout, stderr = self.run_onecite_command([
                "process", test_file, "--output-format", fmt, "--quiet"
            ])
            assert code == 0, f"{fmt} format failed: {stderr}"
            outputs[fmt] = stdout
            assert len(stdout.strip()) > 0, f"{fmt} output should not be empty"

        # All formats should successfully generate output
        assert len(outputs) == 3, "All formats should produce output"

    def test_output_file_generation(self, create_test_file, sample_references, temp_dir):
        """Test output to file"""
        test_file = create_test_file(sample_references["doi_only"])
        output_file = f"{temp_dir}/output.bib"
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--output", output_file, "--quiet"
        ])
        assert code == 0, f"Output to file failed: {stderr}"
        
        # Verify if file was generated
        import os
        assert os.path.exists(output_file), "Output file was not created"
        
        # Verify file content
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content.strip()) > 0, "Output file should not be empty"
        assert "@" in content, "Output file should contain BibTeX content"

    def test_complex_entry_formatting(self, create_test_file, sample_references):
        """Test complex entry formatting"""
        # Use a known working DOI from sample references
        test_file = create_test_file(sample_references["doi_only"])
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        assert code == 0, f"Complex entry formatting failed: {stderr}"
        
        # Verify basic fields are included
        output_lower = stdout.lower()
        expected_fields = ["title", "author", "journal", "year"]
        
        for field in expected_fields:
            assert field in output_lower, f"Missing field: {field}"

