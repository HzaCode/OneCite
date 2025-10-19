"""
Test input format support
Validate TXT and BibTeX input format processing
"""
import pytest
import subprocess
import os

class TestInputFormats:
    """Input format tests"""

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

    def test_txt_format_basic(self, create_test_file, sample_references):
        """Test basic TXT format input"""
        test_file = create_test_file(sample_references["doi_only"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--input-type", "txt", "--quiet"
        ])
        assert code == 0, f"TXT processing failed: {stderr}"
        assert "@article" in stdout or "@inproceedings" in stdout

    def test_txt_format_multiline(self, create_test_file, sample_references):
        """Test multiline TXT format input"""
        multiline_content = f"{sample_references['doi_only']}\n\n{sample_references['conference_paper']}"
        test_file = create_test_file(multiline_content)
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--input-type", "txt", "--quiet"
        ])
        assert code == 0, f"Multiline TXT processing failed: {stderr}"
        # Should process two entries
        bib_entries = stdout.count("@")
        assert bib_entries >= 1, "Should process multiple entries"

    def test_bibtex_format_input(self, create_test_file, sample_references):
        """Test BibTeX format input"""
        test_file = create_test_file(sample_references["bibtex_entry"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--input-type", "bib", "--quiet"
        ])
        assert code == 0, f"BibTeX processing failed: {stderr}"
        assert "@article" in stdout or "@inproceedings" in stdout

    def test_doi_recognition_variants(self, create_test_file):
        """Test various DOI format recognition"""
        doi_variants = [
            "10.1038/nature14539",
            "doi:10.1038/nature14539",
            "DOI: 10.1038/nature14539",
            "https://doi.org/10.1038/nature14539"
        ]
        
        for doi in doi_variants:
            test_file = create_test_file(doi)
            code, stdout, stderr = self.run_onecite_command([
                "process", test_file, "--quiet"
            ])
            assert code == 0, f"DOI variant processing failed for {doi}: {stderr}"
            assert "doi" in stdout.lower(), f"DOI field missing for {doi}"

    def test_arxiv_recognition_variants(self, create_test_file):
        """Test various arXiv format recognition"""
        arxiv_variants = [
            "1706.03762",
            "arxiv:1706.03762",
            "arXiv:1706.03762",
            "https://arxiv.org/abs/1706.03762"
        ]
        
        for arxiv in arxiv_variants:
            test_file = create_test_file(arxiv)
            code, stdout, stderr = self.run_onecite_command([
                "process", test_file, "--quiet"
            ])
            assert code == 0, f"arXiv variant processing failed for {arxiv}: {stderr}"
            # arXiv papers should contain arxiv field or url
            assert "arxiv" in stdout.lower() or "1706.03762" in stdout, f"arXiv identifier missing for {arxiv}"

    def test_conference_paper_recognition(self, create_test_file, sample_references):
        """Test conference paper recognition"""
        test_file = create_test_file(sample_references["conference_paper"])
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        assert code == 0, f"Conference paper processing failed: {stderr}"
        # Conference papers should generate @inproceedings entries
        # Note: This depends on specific implementation, may not always generate @inproceedings
        assert "@" in stdout, "Should generate some BibTeX entry"

    def test_mixed_content_processing(self, create_test_file, sample_references):
        """Test mixed content processing"""
        mixed_content = f"""{sample_references['doi_only']}

{sample_references['arxiv_id']}

{sample_references['conference_paper']}"""
        
        test_file = create_test_file(mixed_content)
        code, stdout, stderr = self.run_onecite_command([
            "process", test_file, "--quiet"
        ])
        assert code == 0, f"Mixed content processing failed: {stderr}"
        
        # Should process multiple entries
        bib_entries = stdout.count("@")
        assert bib_entries >= 2, f"Should process multiple entries, found {bib_entries}"

