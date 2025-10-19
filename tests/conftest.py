"""
Pytest configuration and fixtures for OneCite tests.
"""
import pytest
import sys
import os
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_doi():
    """Sample DOI for testing."""
    return "10.1038/nature14539"


@pytest.fixture
def sample_arxiv():
    """Sample arXiv ID for testing."""
    return "1706.03762"


@pytest.fixture
def sample_text_query():
    """Sample text query for testing."""
    return "Attention is all you need, Vaswani et al., NIPS 2017"


@pytest.fixture
def sample_bibtex():
    """Sample BibTeX entry for testing."""
    return """@article{sample2020,
  title={Sample Article},
  author={Smith, John and Doe, Jane},
  journal={Nature},
  year={2020},
  volume={580},
  pages={1-10}
}"""


@pytest.fixture
def sample_references():
    """Sample references for testing - returns a dictionary."""
    return {
        "doi_only": "10.1038/nature14539",
        "arxiv_id": "1706.03762",
        "conference_paper": "Attention is all you need\nVaswani et al.\nNIPS 2017",
        "bibtex_entry": """@article{sample2020,
  title={Sample Article},
  author={Smith, John and Doe, Jane},
  journal={Nature},
  year={2020},
  volume={580},
  pages={1-10}
}"""
    }


@pytest.fixture
def create_test_file(tmp_path):
    """Factory fixture to create test files."""
    def _create_file(content, filename="test_input.txt"):
        """Create a test file with given content."""
        file_path = tmp_path / filename
        file_path.write_text(content, encoding='utf-8')
        return str(file_path)
    
    return _create_file


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_directory = tempfile.mkdtemp()
    yield temp_directory
    # Cleanup after test
    if os.path.exists(temp_directory):
        shutil.rmtree(temp_directory)
