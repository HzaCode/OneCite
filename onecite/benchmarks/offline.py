"""Offline source fixtures for deterministic benchmark runs."""

from typing import Any, Dict, Optional

CROSSREF_WORK_NATURE_DQN: Dict[str, Any] = {
    "status": "ok",
    "message-type": "work",
    "message": {
        "DOI": "10.1038/nature14236",
        "type": "journal-article",
        "title": ["Human-level control through deep reinforcement learning"],
        "author": [
            {"given": "Volodymyr", "family": "Mnih", "sequence": "first"},
            {"given": "Koray", "family": "Kavukcuoglu", "sequence": "additional"},
            {"given": "David", "family": "Silver", "sequence": "additional"},
        ],
        "container-title": ["Nature"],
        "published-print": {"date-parts": [[2015, 2, 26]]},
        "volume": "518",
        "issue": "7540",
        "page": "529-533",
        "publisher": "Springer Nature",
        "URL": "https://doi.org/10.1038/nature14236",
        "is-referenced-by-count": 100000,
    },
}


CROSSREF_WORK_NATURE_DEEP_LEARNING: Dict[str, Any] = {
    "status": "ok",
    "message-type": "work",
    "message": {
        "DOI": "10.1038/nature14539",
        "type": "journal-article",
        "title": ["Deep learning"],
        "author": [
            {"given": "Yann", "family": "LeCun", "sequence": "first"},
            {"given": "Yoshua", "family": "Bengio", "sequence": "additional"},
            {"given": "Geoffrey", "family": "Hinton", "sequence": "additional"},
        ],
        "container-title": ["Nature"],
        "published-print": {"date-parts": [[2015, 5, 28]]},
        "volume": "521",
        "issue": "7553",
        "page": "436-444",
        "publisher": "Springer Nature",
        "URL": "https://doi.org/10.1038/nature14539",
        "is-referenced-by-count": 100000,
    },
}


CROSSREF_WORK_TRANSFORMER: Dict[str, Any] = {
    "status": "ok",
    "message-type": "work",
    "message": {
        "DOI": "10.5555/3295222.3295349",
        "type": "proceedings-article",
        "title": ["Attention Is All You Need"],
        "author": [
            {"given": "Ashish", "family": "Vaswani", "sequence": "first"},
            {"given": "Noam", "family": "Shazeer", "sequence": "additional"},
            {"given": "Niki", "family": "Parmar", "sequence": "additional"},
        ],
        "container-title": ["Advances in Neural Information Processing Systems"],
        "published-print": {"date-parts": [[2017]]},
        "publisher": "Curran Associates Inc.",
        "URL": "https://dl.acm.org/doi/10.5555/3295222.3295349",
        "is-referenced-by-count": 90000,
    },
}


CROSSREF_SEARCH_TRANSFORMER: Dict[str, Any] = {
    "status": "ok",
    "message-type": "work-list",
    "message": {
        "items": [
            {
                "DOI": "10.5555/3295222.3295349",
                "title": ["Attention Is All You Need"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "container-title": ["Advances in Neural Information Processing Systems"],
                "type": "proceedings-article",
                "issued": {"date-parts": [[2017]]},
                "is-referenced-by-count": 90000,
            }
        ],
    },
}


ARXIV_TRANSFORMER = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <updated>2017-12-06T00:00:00Z</updated>
    <published>2017-06-12T00:00:00Z</published>
    <title>Attention Is All You Need</title>
    <summary>Transformer sequence transduction benchmark fixture.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <author><name>Niki Parmar</name></author>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.5555/3295222.3295349</arxiv:doi>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">15 pages, 5 figures</arxiv:comment>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom"
        term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


SEMANTIC_SCHOLAR_TRANSFORMER: Dict[str, Any] = {
    "data": [
        {
            "title": "Attention Is All You Need",
            "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
            "year": 2017,
            "venue": "NeurIPS",
            "journal": {"name": "Advances in Neural Information Processing Systems"},
            "citationCount": 90000,
            "publicationDate": "2017-06-12",
            "externalIds": {"DOI": "10.5555/3295222.3295349", "ArXiv": "1706.03762"},
            "paperId": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
            "url": "https://www.semanticscholar.org/paper/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        }
    ]
}


PUBMED_SUMMARY_DEEP_LEARNING: Dict[str, Any] = {
    "result": {
        "uids": ["26017442"],
        "26017442": {
            "uid": "26017442",
            "title": "Deep learning.",
            "authors": [
                {"name": "LeCun Y"},
                {"name": "Bengio Y"},
                {"name": "Hinton G"},
            ],
            "fulljournalname": "Nature",
            "source": "Nature",
            "pubdate": "2015 May 28",
            "volume": "521",
            "issue": "7553",
            "pages": "436-444",
            "articleids": [
                {"idtype": "pubmed", "value": "26017442"},
                {"idtype": "doi", "value": "10.1038/nature14539"},
            ],
        },
    }
}


GITHUB_REPO_ONECITE: Dict[str, Any] = {
    "name": "OneCite",
    "full_name": "HzaCode/OneCite",
    "description": "Citation management and academic reference toolkit",
    "owner": {"login": "HzaCode"},
    "created_at": "2026-04-01T00:00:00Z",
    "html_url": "https://github.com/HzaCode/OneCite",
    "language": "Python",
    "stargazers_count": 42,
}


GITHUB_TAGS_ONECITE = [{"name": "v0.1.1"}]


ZENODO_RECORD_ONECITE: Dict[str, Any] = {
    "metadata": {
        "title": "OneCite deterministic benchmark dataset",
        "creators": [{"name": "HzaCode"}],
        "publication_date": "2026-05-20",
        "version": "1.0.0",
        "resource_type": {"type": "dataset"},
    }
}


DATACITE_DRYAD_DATASET: Dict[str, Any] = {
    "data": {
        "attributes": {
            "titles": [{"title": "Data from: Robust citation validation benchmark fixture"}],
            "creators": [{"name": "Dryad Data Repository"}],
            "publicationYear": 2021,
            "publisher": "Dryad",
            "url": "https://doi.org/10.5061/dryad.8gtht76m6",
            "types": {"resourceTypeGeneral": "Dataset"},
        }
    }
}


class OfflineResponse:
    """Small stand-in for ``requests.Response`` used by benchmarks."""

    def __init__(
        self,
        json_data: Optional[Dict[str, Any]] = None,
        text: str = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.json_data = json_data
        self.text = text
        self.content = text.encode("utf-8") if text else b""
        self.status_code = status_code
        self.ok = status_code == 200
        self.headers = headers or {}

    def json(self) -> Dict[str, Any]:
        if self.json_data is None:
            raise ValueError("No JSON data")
        return self.json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(f"HTTP {self.status_code}", response=self)


def offline_requests_get(url: str, *args: Any, **kwargs: Any) -> OfflineResponse:
    """Route benchmark HTTP calls to bundled deterministic fixtures."""
    params = kwargs.get("params", {})
    params_text = str(params)
    normalized_url = url.lower()

    if "api.crossref.org" in normalized_url and "10.1038/nature14236" in normalized_url:
        return OfflineResponse(json_data=CROSSREF_WORK_NATURE_DQN)

    if "api.crossref.org" in normalized_url and "10.1038/nature14539" in normalized_url:
        return OfflineResponse(json_data=CROSSREF_WORK_NATURE_DEEP_LEARNING)

    if "api.crossref.org" in normalized_url and "10.5555/3295222.3295349" in normalized_url:
        return OfflineResponse(json_data=CROSSREF_WORK_TRANSFORMER)

    if "api.crossref.org" in normalized_url and "query" in params_text:
        return OfflineResponse(json_data=CROSSREF_SEARCH_TRANSFORMER)

    if "export.arxiv.org" in normalized_url and "1706.03762" in normalized_url:
        return OfflineResponse(text=ARXIV_TRANSFORMER)

    if "eutils.ncbi.nlm.nih.gov" in normalized_url and "esummary.fcgi" in normalized_url:
        if str(params.get("id")) == "26017442":
            return OfflineResponse(json_data=PUBMED_SUMMARY_DEEP_LEARNING)

    if "api.github.com/repos/hzacode/onecite/tags" in normalized_url:
        return OfflineResponse(json_data=GITHUB_TAGS_ONECITE)

    if "api.github.com/repos/hzacode/onecite" in normalized_url:
        return OfflineResponse(json_data=GITHUB_REPO_ONECITE)

    if "zenodo.org/api/records/3233118" in normalized_url:
        return OfflineResponse(json_data=ZENODO_RECORD_ONECITE)

    if "api.datacite.org/dois/10.5061/dryad.8gtht76m6" in normalized_url:
        return OfflineResponse(json_data=DATACITE_DRYAD_DATASET)

    if "api.semanticscholar.org" in normalized_url:
        return OfflineResponse(json_data=SEMANTIC_SCHOLAR_TRANSFORMER)

    return OfflineResponse(json_data={}, status_code=404)
