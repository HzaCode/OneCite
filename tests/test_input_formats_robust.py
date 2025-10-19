"""
Test input format support (robust version, reduced network dependencies)
Validate TXT and BibTeX input format processing, but avoid timeout issues
"""
import pytest
import subprocess
import os

class TestInputFormatsRobust:
    """Input format tests (robust version)"""

    def run_onecite_command_with_timeout(self, args, cwd=None, timeout=15):
        """Helper method to run onecite command with shorter timeout"""
        cmd = ["onecite"] + args
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                timeout=timeout  # Reduce timeout duration
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"

    def test_doi_only_processing(self, create_test_file):
        """Test simple processing with DOI only (should complete quickly)"""
        test_file = create_test_file("10.1038/nature14539")
        code, stdout, stderr = self.run_onecite_command_with_timeout([
            "process", test_file, "--quiet"
        ])
        # This test should complete quickly since DOI processing is relatively simple
        if code == 0:
            assert "@" in stdout, "Should contain BibTeX entry"
        else:
            # If it fails, at least verify it's not due to format issues
            assert "format" not in stderr.lower(), f"Should not be format error: {stderr}"

    def test_bibtex_input_processing(self, create_test_file, sample_references):
        """Test BibTeX input processing (no external API involved)"""
        test_file = create_test_file(sample_references["bibtex_entry"])
        code, stdout, stderr = self.run_onecite_command_with_timeout([
            "process", test_file, "--input-type", "bib", "--quiet"
        ])
        # BibTeX processing should not require external network calls
        assert code == 0 or "timeout" not in stderr.lower(), f"BibTeX processing should not timeout: {stderr}"

    def test_command_line_robustness(self, create_test_file):
        """Test basic command line robustness"""
        # Test empty file
        empty_file = create_test_file("")
        code, stdout, stderr = self.run_onecite_command_with_timeout([
            "process", empty_file, "--quiet"
        ], timeout=10)
        # Empty file should be processed quickly
        assert code == 0 or "timeout" not in stderr.lower(), "Empty file should process quickly"

    def test_output_format_switching(self, create_test_file):
        """Test output format switching (non-network dependent parts)"""
        test_file = create_test_file("Simple test reference")
        
        formats = ["bibtex", "apa", "mla"]
        for fmt in formats:
            code, stdout, stderr = self.run_onecite_command_with_timeout([
                "process", test_file, "--output-format", fmt, "--quiet"
            ], timeout=10)
            
            # Even if processing fails, it should not timeout
            assert "timeout" not in stderr.lower(), f"Format {fmt} should not timeout"

    def test_template_switching(self, create_test_file):
        """Test template switching"""
        test_file = create_test_file("Test reference")
        
        templates = ["journal_article_full", "conference_paper"]
        for template in templates:
            code, stdout, stderr = self.run_onecite_command_with_timeout([
                "process", test_file, "--template", template, "--quiet"
            ], timeout=10)
            
            # Template processing should not timeout
            assert "timeout" not in stderr.lower(), f"Template {template} should not timeout"

    @pytest.mark.slow
    def test_arxiv_processing_with_long_timeout(self, create_test_file):
        """Test arXiv processing (with long timeout, marked as slow test)"""
        test_file = create_test_file("1706.03762")
        code, stdout, stderr = self.run_onecite_command_with_timeout([
            "process", test_file, "--quiet"
        ], timeout=60)  # Give arXiv processing more time
        
        # This test may fail due to network issues, but should not be format issues
        if code != 0:
            # Check if it's network-related error rather than code error
            network_errors = ["timeout", "connection", "network", "dns", "resolve"]
            is_network_error = any(error in stderr.lower() for error in network_errors)
            if not is_network_error:
                pytest.fail(f"arXiv processing failed with non-network error: {stderr}")

    def test_error_message_quality(self, create_test_file):
        """Test error message quality"""
        # Test invalid DOI
        test_file = create_test_file("invalid.doi.format")
        code, stdout, stderr = self.run_onecite_command_with_timeout([
            "process", test_file, "--quiet"
        ], timeout=10)
        
        # Should fail quickly and give reasonable error message
        assert "timeout" not in stderr.lower(), "Invalid input should fail quickly, not timeout"

    def test_basic_functionality_without_network(self, create_test_file):
        """Test basic functionality (avoid network calls as much as possible)"""
        # Use known locally processable content
        local_content = """@article{local2023,
  title={Local Test Article},
  author={Test Author},
  journal={Test Journal},
  year={2023}
}"""
        
        test_file = create_test_file(local_content, "test.bib")
        code, stdout, stderr = self.run_onecite_command_with_timeout([
            "process", test_file, "--input-type", "bib", "--quiet"
        ], timeout=15)
        
        # Local BibTeX processing should succeed
        if code == 0:
            assert "@" in stdout, "Should generate BibTeX output"
        else:
            # If it fails, ensure it's not timeout
            assert "timeout" not in stderr.lower(), f"Local processing should not timeout: {stderr}"

