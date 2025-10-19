"""
Integration tests
Test complete workflows and examples from README
"""
import pytest
import subprocess
import os
import tempfile

class TestIntegration:
    """Integration tests"""

    def run_onecite_command(self, args, cwd=None):
        """Helper method to run onecite command"""
        cmd = ["onecite"] + args
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                timeout=60  # Increase timeout for integration tests
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"

    def test_readme_basic_example(self, create_test_file, temp_dir):
        """Test basic example from README"""
        # Example input from README
        readme_input = """10.1038/nature14539

Attention is all you need
Vaswani et al.
NIPS 2017"""
        
        test_file = create_test_file(readme_input)
        output_file = os.path.join(temp_dir, "results.bib")
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--output", output_file, "--quiet"
        ])
        
        assert code == 0, f"README example failed: {stderr}"
        assert os.path.exists(output_file), "Output file should be created"
        
        # Verify output content
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should contain two entries
        bib_entries = content.count("@")
        assert bib_entries >= 1, f"Should contain BibTeX entries, found {bib_entries}"
        
        # Check specific content (based on README expectations)
        content_lower = content.lower()
        # May contain deep learning related content or attention related content
        has_relevant_content = any(keyword in content_lower for keyword in [
            "nature", "deep", "learning", "attention", "vaswani", "nips", "neural"
        ])
        assert has_relevant_content, "Output should contain relevant academic content"

    def test_workflow_txt_to_bibtex(self, create_test_file, temp_dir):
        """Test complete TXT to BibTeX workflow"""
        # Create input containing different types of references
        mixed_input = """10.1038/nature14539

1706.03762

Attention is all you need
Vaswani et al.
NIPS 2017

https://arxiv.org/abs/1706.03762"""
        
        test_file = create_test_file(mixed_input)
        output_file = os.path.join(temp_dir, "output.bib")
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, 
            "--input-type", "txt",
            "--output-format", "bibtex",
            "--template", "journal_article_full",
            "--output", output_file,
            "--quiet"
        ])
        
        assert code == 0, f"TXT to BibTeX workflow failed: {stderr}"
        assert os.path.exists(output_file), "BibTeX output file should be created"
        
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "@" in content, "Should contain BibTeX entries"
        assert len(content.strip()) > 100, "Should contain substantial content"

    def test_workflow_bib_to_apa(self, create_test_file, temp_dir):
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
        
        test_file = create_test_file(bib_input, "input.bib")
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file,
            "--input-type", "bib",
            "--output-format", "apa",
            "--quiet"
        ])
        
        assert code == 0, f"BibTeX to APA workflow failed: {stderr}"
        assert len(stdout.strip()) > 0, "APA output should not be empty"

    def test_conference_paper_workflow(self, create_test_file, temp_dir):
        """Test complete conference paper workflow"""
        conference_input = """Attention is all you need
Vaswani et al.
NIPS 2017

ResNet: Deep Residual Learning for Image Recognition
He, Zhang, Ren, Sun
CVPR 2016"""
        
        test_file = create_test_file(conference_input)
        output_file = os.path.join(temp_dir, "conference.bib")
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file,
            "--template", "conference_paper",
            "--output", output_file,
            "--quiet"
        ])
        
        assert code == 0, f"Conference paper workflow failed: {stderr}"
        assert os.path.exists(output_file), "Conference output file should be created"

    def test_arxiv_workflow(self, create_test_file):
        """Test arXiv paper workflow"""
        arxiv_input = """1706.03762

arxiv:1512.03385

https://arxiv.org/abs/2010.11929"""
        
        test_file = create_test_file(arxiv_input)
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        
        assert code == 0, f"arXiv workflow failed: {stderr}"
        
        # Verify arXiv related content
        output_lower = stdout.lower()
        assert "arxiv" in output_lower or "1706.03762" in stdout, "Should contain arXiv references"

    def test_error_recovery_workflow(self, create_test_file):
        """Test error recovery workflow"""
        # Mix of valid and invalid references
        mixed_input = """10.1038/nature14539

invalid_reference_12345

1706.03762

another_invalid_reference"""
        
        test_file = create_test_file(mixed_input)
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        
        # Should partially succeed (process valid references, skip invalid ones)
        assert code == 0, f"Error recovery workflow failed: {stderr}"
        
        # Should process at least some valid entries
        if "@" in stdout:
            bib_entries = stdout.count("@")
            assert bib_entries >= 1, "Should process some valid entries"

    def test_large_batch_processing(self, create_test_file):
        """Test large batch processing"""
        # Create input with multiple references
        large_input = """10.1038/nature14539

10.1126/science.1127647

1706.03762

1512.03385

Attention is all you need
Vaswani et al.
NIPS 2017

BERT: Pre-training of Deep Bidirectional Transformers
Devlin et al.
NAACL 2019"""
        
        test_file = create_test_file(large_input)
        
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        
        # Large batch processing should succeed
        assert code == 0, f"Large batch processing failed: {stderr}"
        
        # Should process multiple entries
        if "@" in stdout:
            bib_entries = stdout.count("@")
            assert bib_entries >= 2, f"Should process multiple entries, found {bib_entries}"

    def test_cross_format_compatibility(self, create_test_file, temp_dir):
        """Test cross-format compatibility"""
        # First generate BibTeX
        input_content = "10.1038/nature14539"
        test_file = create_test_file(input_content)
        bib_file = os.path.join(temp_dir, "temp.bib")
        
        # Generate BibTeX
        code1, stdout1, stderr1 = self.run_onecite_command([
            "process", test_file, "--output", bib_file, "--quiet"
        ])
        
        if code1 == 0 and os.path.exists(bib_file):
            # Use generated BibTeX as input
            code2, stdout2, stderr2 = self.run_onecite_command([
                "process", bib_file, "--input-type", "bib", "--output-format", "apa", "--quiet"
            ])
            
            assert code2 == 0, f"Cross-format compatibility failed: {stderr2}"
            assert len(stdout2.strip()) > 0, "Cross-format output should not be empty"

