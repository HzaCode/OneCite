"""
Test Python API
Verify process_references function and related APIs
"""
import pytest
from unittest.mock import Mock

class TestPythonAPI:
    """Python API tests"""

    def test_api_import(self):
        """Test API import"""
        try:
            from onecite import process_references
            assert callable(process_references), "process_references should be callable"
        except ImportError as e:
            pytest.fail(f"Failed to import API: {e}")

    def test_api_basic_functionality(self, sample_references):
        """Test API basic functionality"""
        try:
            from onecite import process_references
            
            def mock_callback(candidates):
                return 0  # Always choose the first candidate
            
            result = process_references(
                input_content=sample_references["doi_only"],
                input_type="txt",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=mock_callback
            )
            
            # Verify return structure
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "results" in result, "Result should contain 'results' key"
            assert "report" in result, "Result should contain 'report' key"
            
            # Verify report structure
            report = result["report"]
            assert "total" in report, "Report should contain 'total'"
            assert "succeeded" in report, "Report should contain 'succeeded'"
            assert "failed_entries" in report, "Report should contain 'failed_entries'"
            
            # Verify result types
            assert isinstance(result["results"], list), "Results should be a list"
            assert isinstance(report["total"], int), "Total should be an integer"
            assert isinstance(report["succeeded"], int), "Succeeded should be an integer"
            assert isinstance(report["failed_entries"], list), "Failed entries should be a list"
            
        except ImportError:
            pytest.skip("API not available for testing")

    def test_api_with_bibtex_input(self, sample_references):
        """Test API with BibTeX input"""
        try:
            from onecite import process_references
            
            def mock_callback(candidates):
                return 0
            
            result = process_references(
                input_content=sample_references["bibtex_entry"],
                input_type="bib",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=mock_callback
            )
            
            assert result["report"]["total"] >= 1, "Should process at least one entry"
            
        except ImportError:
            pytest.skip("API not available for testing")

    def test_api_different_output_formats(self, sample_references):
        """Test API with different output formats"""
        try:
            from onecite import process_references
            
            def mock_callback(candidates):
                return 0
            
            formats = ["bibtex", "apa", "mla"]
            
            for fmt in formats:
                result = process_references(
                    input_content=sample_references["doi_only"],
                    input_type="txt",
                    template_name="journal_article_full",
                    output_format=fmt,
                    interactive_callback=mock_callback
                )
                
                assert isinstance(result["results"], list), f"Results should be list for {fmt}"
                # Should at least attempt to process entries (even if failed)
                assert result["report"]["total"] >= 1, f"Should process entry for {fmt}"
                
        except ImportError:
            pytest.skip("API not available for testing")

    def test_api_interactive_callback(self, sample_references):
        """Test interactive callback functionality"""
        try:
            from onecite import process_references
            
            callback_called = []
            
            def test_callback(candidates):
                callback_called.append(len(candidates))
                return 0  # Choose the first one
            
            result = process_references(
                input_content="Some ambiguous reference that might trigger callback",
                input_type="txt",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=test_callback
            )
            
            # Callback may or may not be called, depending on whether there are ambiguities
            # But the function should execute successfully
            assert isinstance(result, dict), "Should return result dictionary"
            
        except ImportError:
            pytest.skip("API not available for testing")

    def test_api_error_handling(self):
        """Test API error handling"""
        try:
            from onecite import process_references
            
            def mock_callback(candidates):
                return 0
            
            # Test invalid input type
            with pytest.raises(Exception):  # Should raise some exception
                process_references(
                    input_content="test",
                    input_type="invalid_type",
                    template_name="journal_article_full",
                    output_format="bibtex",
                    interactive_callback=mock_callback
                )
                
        except ImportError:
            pytest.skip("API not available for testing")

    def test_api_empty_input(self):
        """Test empty input handling"""
        try:
            from onecite import process_references
            
            def mock_callback(candidates):
                return 0
            
            result = process_references(
                input_content="",
                input_type="txt",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=mock_callback
            )
            
            # Empty input should return empty results but not crash
            assert result["report"]["total"] == 0, "Empty input should result in 0 total"
            assert len(result["results"]) == 0, "Empty input should result in empty results"
            
        except ImportError:
            pytest.skip("API not available for testing")

    def test_api_multiple_entries(self, sample_references):
        """Test multiple entries processing"""
        try:
            from onecite import process_references
            
            def mock_callback(candidates):
                return 0
            
            # Combine multiple references
            multi_content = f"{sample_references['doi_only']}\n\n{sample_references['arxiv_id']}"
            
            result = process_references(
                input_content=multi_content,
                input_type="txt",
                template_name="journal_article_full",
                output_format="bibtex",
                interactive_callback=mock_callback
            )
            
            # Should process multiple entries
            assert result["report"]["total"] >= 2, "Should process multiple entries"
            
        except ImportError:
            pytest.skip("API not available for testing")

