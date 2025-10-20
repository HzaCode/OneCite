"""
Integration tests
Test complete workflows and examples from README
"""
import pytest
import os
import tempfile
from unittest.mock import patch
from .mock_responses import mock_requests_get

class TestIntegration:
    """Integration tests"""

    def run_onecite_process(self, input_content, input_type="txt", output_format="bibtex", template="journal_article_full"):
        """Helper method to run onecite processing with mocked API calls"""
        try:
            # Mock requests.get to avoid real API calls
            with patch('requests.get', side_effect=mock_requests_get):
                from onecite import process_references
                
                def mock_callback(candidates):
                    return 0  # Always choose the first candidate
                
                result = process_references(
                    input_content=input_content,
                    input_type=input_type,
                    template_name=template,
                    output_format=output_format,
                    interactive_callback=mock_callback
                )
                
                # Simulate CLI output
                output_content = '\n\n'.join(result['results'])
                return 0, output_content, "", result
        except Exception as e:
            return 1, "", str(e), None

    def test_readme_basic_example(self):
        """Test basic example from README"""
        # Example input from README
        readme_input = """10.1038/nature14539

Attention is all you need
Vaswani et al.
NIPS 2017"""
        
        code, stdout, stderr, result = self.run_onecite_process(readme_input)
        
        assert code == 0, f"README example failed: {stderr}"
        
        # Should contain entries or at least attempt processing
        assert result is not None, "Should return result"
        assert result['report']['total'] >= 1, "Should process at least one entry"

    def test_workflow_txt_to_bibtex(self):
        """Test complete TXT to BibTeX workflow"""
        # Create input containing different types of references
        mixed_input = """10.1038/nature14539

1706.03762"""
        
        code, stdout, stderr, result = self.run_onecite_process(
            mixed_input, input_type="txt", output_format="bibtex"
        )
        
        assert code == 0, f"TXT to BibTeX workflow failed: {stderr}"
        assert result is not None, "Should return result"

    def test_workflow_bib_to_apa(self):
        """Test BibTeX to APA workflow"""
        # Create BibTeX input
        bib_input = """@article{test2015,
  title={Deep learning},
  author={LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
  journal={Nature},
  year={2015},
  volume={521},
  pages={436--444},
  doi={10.1038/nature14539}
}"""
        
        code, stdout, stderr, result = self.run_onecite_process(
            bib_input, input_type="bib", output_format="apa"
        )
        
        assert code == 0, f"BibTeX to APA workflow failed: {stderr}"
        assert result is not None, "Should return result"

    def test_conference_paper_workflow(self):
        """Test complete conference paper workflow"""
        conference_input = """Attention is all you need
Vaswani et al.
NIPS 2017"""
        
        code, stdout, stderr, result = self.run_onecite_process(
            conference_input, template="conference_paper"
        )
        
        assert code == 0, f"Conference paper workflow failed: {stderr}"
        assert result is not None, "Should return result"

    def test_arxiv_workflow(self):
        """Test arXiv paper workflow"""
        arxiv_input = """1706.03762

arxiv:1512.03385"""
        
        code, stdout, stderr, result = self.run_onecite_process(arxiv_input)
        
        assert code == 0, f"arXiv workflow failed: {stderr}"
        assert result is not None, "Should return result"

    def test_error_recovery_workflow(self):
        """Test error recovery workflow"""
        # Mix of valid and invalid references
        mixed_input = """10.1038/nature14539

invalid_reference_12345

1706.03762"""
        
        code, stdout, stderr, result = self.run_onecite_process(mixed_input)
        
        # Should partially succeed (process valid references, skip invalid ones)
        assert code == 0, f"Error recovery workflow failed: {stderr}"
        assert result is not None, "Should return result"

    def test_large_batch_processing(self):
        """Test large batch processing"""
        # Create input with multiple references
        large_input = """10.1038/nature14539

1706.03762

Attention is all you need
Vaswani et al.
NIPS 2017"""
        
        code, stdout, stderr, result = self.run_onecite_process(large_input)
        
        # Large batch processing should succeed
        assert code == 0, f"Large batch processing failed: {stderr}"
        assert result is not None, "Should return result"
        # Should process multiple entries
        assert result['report']['total'] >= 2, "Should process multiple entries"

    def test_cross_format_compatibility(self):
        """Test cross-format compatibility"""
        # First generate BibTeX
        input_content = "10.1038/nature14539"
        
        # Generate BibTeX
        code1, stdout1, stderr1, result1 = self.run_onecite_process(
            input_content, output_format="bibtex"
        )
        
        if code1 == 0 and stdout1:
            # Use generated BibTeX as input
            code2, stdout2, stderr2, result2 = self.run_onecite_process(
                stdout1, input_type="bib", output_format="apa"
            )
            
            assert code2 == 0, f"Cross-format compatibility failed: {stderr2}"
            assert result2 is not None, "Should return result"
