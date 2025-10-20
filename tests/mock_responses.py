"""
Mock responses for external API calls in tests.
This module provides mock data to simulate API responses from Crossref, arXiv, etc.
"""

# Mock Crossref API response for DOI 10.1038/nature14539
MOCK_CROSSREF_RESPONSE = {
    "status": "ok",
    "message-type": "work",
    "message": {
        "DOI": "10.1038/nature14539",
        "type": "journal-article",
        "title": ["Human-level control through deep reinforcement learning"],
        "author": [
            {"given": "Volodymyr", "family": "Mnih", "sequence": "first"},
            {"given": "Koray", "family": "Kavukcuoglu", "sequence": "additional"},
            {"given": "David", "family": "Silver", "sequence": "additional"}
        ],
        "container-title": ["Nature"],
        "published-print": {"date-parts": [[2015, 2, 26]]},
        "volume": "518",
        "issue": "7540",
        "page": "529-533",
        "publisher": "Springer Nature",
        "ISSN": ["0028-0836", "1476-4687"]
    }
}

# Mock arXiv API response for 1706.03762
MOCK_ARXIV_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <updated>2017-12-06T00:00:00Z</updated>
    <published>2017-06-12T00:00:00Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.</summary>
    <author>
      <name>Ashish Vaswani</name>
    </author>
    <author>
      <name>Noam Shazeer</name>
    </author>
    <author>
      <name>Niki Parmar</name>
    </author>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.5555/3295222.3295349</arxiv:doi>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">15 pages, 5 figures</arxiv:comment>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""

# Mock BibTeX output for DOI
MOCK_BIBTEX_DOI = """@article{Mnih2015,
  author = {Mnih, Volodymyr and Kavukcuoglu, Koray and Silver, David},
  title = {Human-level control through deep reinforcement learning},
  journal = {Nature},
  year = {2015},
  volume = {518},
  number = {7540},
  pages = {529--533},
  doi = {10.1038/nature14539},
  publisher = {Springer Nature}
}"""

# Mock BibTeX output for arXiv
MOCK_BIBTEX_ARXIV = """@article{Vaswani2017,
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  title = {Attention Is All You Need},
  journal = {arXiv preprint arXiv:1706.03762},
  year = {2017},
  url = {https://arxiv.org/abs/1706.03762}
}"""

# Mock response for conference paper
MOCK_BIBTEX_CONFERENCE = """@inproceedings{Vaswani2017,
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  title = {Attention Is All You Need},
  booktitle = {Advances in Neural Information Processing Systems},
  year = {2017},
  pages = {5998--6008}
}"""


def mock_requests_get(url, *args, **kwargs):
    """Mock requests.get function"""
    class MockResponse:
        def __init__(self, json_data=None, text="", status_code=200):
            self.json_data = json_data
            self.text = text
            self.content = text.encode('utf-8') if text else b""
            self.status_code = status_code
            self.ok = status_code == 200
        
        def json(self):
            if self.json_data is None:
                raise ValueError("No JSON data")
            return self.json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    # Mock Crossref API
    if "api.crossref.org" in url and "10.1038/nature14539" in url:
        return MockResponse(json_data=MOCK_CROSSREF_RESPONSE)
    
    # Mock arXiv API
    if "export.arxiv.org" in url and "1706.03762" in url:
        return MockResponse(text=MOCK_ARXIV_RESPONSE)
    
    # Default: return empty response
    return MockResponse(json_data={}, status_code=404)


def get_mock_bibtex_output(input_text):
    """Get mock BibTeX output based on input"""
    input_lower = input_text.lower()
    
    if "10.1038/nature14539" in input_lower:
        return MOCK_BIBTEX_DOI
    elif "1706.03762" in input_lower or "arxiv" in input_lower:
        return MOCK_BIBTEX_ARXIV
    elif "attention" in input_lower and "need" in input_lower:
        return MOCK_BIBTEX_CONFERENCE
    
    # Default: return a generic BibTeX entry
    return """@article{Unknown,
  author = {Unknown Author},
  title = {Unknown Title},
  journal = {Unknown Journal},
  year = {2020}
}"""

