import random
import string
from unittest.mock import patch

import bibtexparser

from onecite.pipeline import EnricherModule, FormatterModule, ParserModule

SEED = 20260603


def _word(rng, min_len=4, max_len=10):
    letters = string.ascii_lowercase
    return "".join(rng.choice(letters) for _ in range(rng.randint(min_len, max_len)))


def _title(rng, i):
    words = [_word(rng).capitalize() for _ in range(rng.randint(4, 8))]
    return f"{' '.join(words)} Study {i}"


def _author(rng, i):
    first = _word(rng).capitalize()
    last = f"{_word(rng).capitalize()}{i}"
    return f"{last}, {first}"


def _doi(rng, i):
    suffix = f"{_word(rng, 5, 8)}.{rng.randint(1000, 9999)}.{i}"
    return f"10.{rng.randint(1000, 9999)}/{suffix}"


def test_randomized_text_parser_extracts_expected_identifiers():
    rng = random.Random(SEED)
    parser = ParserModule()
    blocks = []
    cases = []

    for i in range(64):
        title = _title(rng, i)
        author = _author(rng, i)
        year = str(rng.randint(1990, 2026))
        kind = rng.choice(("doi", "url", "plain", "pmid"))

        if kind == "doi":
            doi = _doi(rng, i)
            trailing = rng.choice((".", ";", ")", "]", ""))
            block = f"{title}\n{author}\nPublished {year}. doi: {doi}{trailing}"
            cases.append({"kind": kind, "doi": doi, "url": None, "query": None})
        elif kind == "url":
            url = f"https://example.org/{_word(rng)}/{i}"
            block = f"{title}\n{author}\nAvailable at {url}"
            cases.append({"kind": kind, "doi": None, "url": url, "query": None})
        elif kind == "pmid":
            pmid = str(rng.randint(1_000_000, 99_999_999))
            block = f"PMID: {pmid}"
            cases.append({"kind": kind, "doi": None, "url": None, "query": block})
        else:
            block = f"{title}\n{author}\nJournal of {_word(rng).capitalize()}, {year}"
            cases.append(
                {
                    "kind": kind,
                    "doi": None,
                    "url": None,
                    "query": f"{title} {author} {year}",
                }
            )

        blocks.append(block)

    entries = parser.parse("\n\n".join(blocks), "txt")

    assert len(entries) == len(cases)
    for entry, expected in zip(entries, cases):
        assert entry["doi"] == expected["doi"]
        assert entry["url"] == expected["url"]
        assert entry.get("query_string") == expected["query"]


def test_randomized_metadata_enrichment_stays_complete_without_network():
    rng = random.Random(SEED + 1)
    template = {"entry_type": "@article", "fields": []}
    identified_entries = []
    raw_entries = []
    kinds = []

    for i in range(48):
        title = _title(rng, i)
        year = str(rng.randint(1990, 2026))
        kind = rng.choice(("article", "conference", "book", "dataset"))
        kinds.append(kind)
        metadata = {
            "title": title,
            "authors": [_author(rng, i), _author(rng, i + 100)],
            "year": year,
            "doi": _doi(rng, i),
            "url": f"https://example.org/work/{i}",
            "pages": f"{rng.randint(1, 200)}--{rng.randint(201, 400)}",
        }

        if kind == "article":
            metadata.update({"type": "journal-article", "journal": "Journal of Random Tests"})
        elif kind == "conference":
            metadata.update({"type": "proceedings-article", "journal": "Random Test Conference"})
        elif kind == "book":
            metadata.update({"type": "book", "publisher": "Example Press"})
        else:
            metadata.update({"type": "dataset", "publisher": "Example Repository"})

        identified_entries.append(
            {
                "id": i,
                "raw_text": title,
                "doi": None,
                "arxiv_id": None,
                "url": None,
                "metadata": metadata,
                "status": "identified",
            }
        )
        raw_entries.append({"id": i, "raw_text": title, "doi": None, "url": None})

    with patch(
        "onecite.pipeline.requests.get",
        side_effect=AssertionError("unexpected network call in randomized enrichment test"),
    ) as mock_get:
        completed = EnricherModule().enrich(identified_entries, template, raw_entries)
        mock_get.assert_not_called()

    assert len(completed) == len(identified_entries)
    assert all(entry["status"] == "completed" for entry in completed)
    assert len({entry["bib_key"] for entry in completed}) == len(completed)
    for entry, kind in zip(completed, kinds):
        bib_data = entry["bib_data"]
        assert bib_data["title"]
        assert bib_data["author"]
        assert bib_data["year"]
        assert bib_data["doi"].startswith("10.")
        if kind == "article":
            assert bib_data["ENTRYTYPE"] == "article"
            assert bib_data["journal"]
        elif kind == "conference":
            assert bib_data["ENTRYTYPE"] == "inproceedings"
            assert bib_data["booktitle"]
            assert "journal" not in bib_data
        elif kind == "book":
            assert bib_data["ENTRYTYPE"] == "book"
            assert bib_data["publisher"]
        else:
            assert bib_data["ENTRYTYPE"] == "misc"
            assert bib_data["howpublished"]


def test_entry_type_edge_case_matrix_without_network():
    cases = [
        {
            "name": "journal article",
            "metadata": {
                "title": "Journal matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "type": "journal-article",
                "journal": "Journal of Matrix Tests",
            },
            "raw_entry": {},
            "entry_type": "article",
            "journal": "Journal of Matrix Tests",
            "booktitle": None,
        },
        {
            "name": "metadata conference type",
            "metadata": {
                "title": "Conference matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "type": "conference",
                "journal": "International Matrix Conference",
            },
            "raw_entry": {},
            "entry_type": "inproceedings",
            "journal": None,
            "booktitle": "International Matrix Conference",
        },
        {
            "name": "metadata proceedings article type",
            "metadata": {
                "title": "Proceedings matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "type": "proceedings-article",
                "journal": "Proceedings of Matrix Tests",
            },
            "raw_entry": {},
            "entry_type": "inproceedings",
            "journal": None,
            "booktitle": "Proceedings of Matrix Tests",
        },
        {
            "name": "booktitle already present",
            "metadata": {
                "title": "Booktitle matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "booktitle": "Workshop on Matrix Tests",
            },
            "raw_entry": {},
            "entry_type": "inproceedings",
            "journal": None,
            "booktitle": "Workshop on Matrix Tests",
        },
        {
            "name": "raw base record proceedings type",
            "metadata": {
                "title": "Base record matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "journal": "Base Record Proceedings",
            },
            "raw_entry": {"type": "proceedings-article"},
            "entry_type": "inproceedings",
            "journal": None,
            "booktitle": "Base Record Proceedings",
        },
        {
            "name": "dataset",
            "metadata": {
                "title": "Dataset matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "type": "dataset",
                "url": "https://example.org/dataset",
            },
            "raw_entry": {},
            "entry_type": "misc",
            "journal": None,
            "booktitle": None,
        },
        {
            "name": "book",
            "metadata": {
                "title": "Book matrix case",
                "authors": ["Doe, Jane"],
                "year": "2024",
                "type": "book",
                "publisher": "Matrix Press",
            },
            "raw_entry": {},
            "entry_type": "book",
            "journal": None,
            "booktitle": None,
        },
    ]
    identified_entries = []
    raw_entries = []

    for i, case in enumerate(cases):
        identified_entries.append(
            {
                "id": i,
                "raw_text": case["name"],
                "doi": None,
                "arxiv_id": None,
                "url": None,
                "metadata": case["metadata"],
                "status": "identified",
            }
        )
        raw_entries.append(
            {
                "id": i,
                "raw_text": case["name"],
                "doi": None,
                "url": None,
                **case["raw_entry"],
            }
        )

    with patch(
        "onecite.pipeline.requests.get",
        side_effect=AssertionError("unexpected network call in entry type matrix test"),
    ) as mock_get:
        completed = EnricherModule().enrich(
            identified_entries,
            {"entry_type": "@article", "fields": []},
            raw_entries,
        )
        mock_get.assert_not_called()

    assert len(completed) == len(cases)
    for entry, case in zip(completed, cases):
        bib_data = entry["bib_data"]
        assert bib_data["ENTRYTYPE"] == case["entry_type"], case["name"]
        if case["journal"] is None:
            assert "journal" not in bib_data, case["name"]
        else:
            assert bib_data["journal"] == case["journal"]
        if case["booktitle"] is None:
            assert "booktitle" not in bib_data, case["name"]
        else:
            assert bib_data["booktitle"] == case["booktitle"]


def test_crossref_proceedings_article_becomes_inproceedings_without_network():
    enricher = EnricherModule()
    identified_entries = [
        {
            "id": 1,
            "raw_text": "Proceedings paper",
            "doi": "10.1234/example.1",
            "arxiv_id": None,
            "url": None,
            "metadata": {},
            "status": "identified",
        }
    ]
    raw_entries = [
        {
            "id": 1,
            "raw_text": "Proceedings paper",
            "doi": "10.1234/example.1",
            "url": None,
        }
    ]
    crossref_record = {
        "title": "Proceedings paper",
        "author": "Doe, Jane",
        "year": "2024",
        "doi": "10.1234/example.1",
        "journal": "ACM SenSys",
        "type": "proceedings-article",
        "abstract": "Already present, so no abstract fallback is needed.",
    }

    with (
        patch.object(enricher, "_get_crossref_metadata", return_value=crossref_record),
        patch(
            "onecite.pipeline.requests.get",
            side_effect=AssertionError("unexpected network call"),
        ) as mock_get,
    ):
        completed = enricher.enrich(
            identified_entries,
            {"entry_type": "@article", "fields": []},
            raw_entries,
        )
        mock_get.assert_not_called()

    bib_data = completed[0]["bib_data"]
    assert bib_data["ENTRYTYPE"] == "inproceedings"
    assert bib_data["booktitle"] == "ACM SenSys"
    assert "journal" not in bib_data


def test_randomized_bibtex_formatter_outputs_parseable_records():
    rng = random.Random(SEED + 2)
    formatter = FormatterModule()
    completed_entries = []

    for i in range(52):
        entry_type = rng.choice(("article", "inproceedings", "book", "misc"))
        bib_key = f"Rand{rng.randint(1990, 2026)}{i}"
        bib_data = {
            "ENTRYTYPE": entry_type,
            "ID": bib_key,
            "title": _title(rng, i),
            "author": f"{_author(rng, i)} and {_author(rng, i + 100)}",
            "year": str(rng.randint(1990, 2026)),
            "doi": _doi(rng, i),
            "pages": f"{rng.randint(1, 200)}--{rng.randint(201, 400)}",
        }
        if entry_type == "article":
            bib_data["journal"] = "Journal of Random Tests"
        elif entry_type == "inproceedings":
            bib_data["booktitle"] = "Proceedings of Random Tests"
        elif entry_type == "book":
            bib_data["publisher"] = "Example Press"
        else:
            bib_data["howpublished"] = "Online"

        completed_entries.append(
            {
                "id": i,
                "doi": bib_data["doi"],
                "status": "completed",
                "bib_key": bib_key,
                "bib_data": bib_data,
            }
        )

    result = formatter.format(completed_entries, "bibtex")
    parsed = bibtexparser.loads("\n\n".join(result["results"]))

    assert result["report"] == {
        "total": len(completed_entries),
        "succeeded": len(completed_entries),
        "failed_entries": [],
    }
    assert len(parsed.entries) == len(completed_entries)
    assert {entry["ID"] for entry in parsed.entries} == {
        entry["bib_key"] for entry in completed_entries
    }
    assert all(entry["doi"].startswith("10.") for entry in parsed.entries)


def test_parser_bibtex_round_trip_integrity():
    rng = random.Random(SEED + 3)
    formatter = FormatterModule()
    expected_by_id = {}
    completed_entries = []

    for i in range(32):
        entry_type = ("article", "inproceedings", "book", "misc")[i % 4]
        bib_key = f"RoundTrip{rng.randint(1990, 2026)}{i}"
        bib_data = {
            "ENTRYTYPE": entry_type,
            "ID": bib_key,
            "title": _title(rng, i),
            "author": f"{_author(rng, i)} and {_author(rng, i + 100)}",
            "year": str(rng.randint(1990, 2026)),
            "doi": _doi(rng, i),
        }

        if entry_type == "article":
            bib_data["journal"] = "Journal of Round Trip Tests"
        elif entry_type == "inproceedings":
            bib_data["booktitle"] = "Proceedings of Round Trip Tests"
        elif entry_type == "book":
            bib_data["publisher"] = "Round Trip Press"
        else:
            bib_data["howpublished"] = "Online"

        expected_by_id[bib_key] = bib_data
        completed_entries.append(
            {
                "id": i,
                "doi": bib_data["doi"],
                "status": "completed",
                "bib_key": bib_key,
                "bib_data": bib_data,
            }
        )

    formatted = formatter.format(completed_entries, "bibtex")
    parsed_entries = ParserModule().parse("\n\n".join(formatted["results"]), "bib")

    assert formatted["report"]["failed_entries"] == []
    assert len(parsed_entries) == len(completed_entries)
    for parsed_entry in parsed_entries:
        original_entry = parsed_entry["original_entry"]
        expected = expected_by_id[original_entry["ID"]]
        for field in ("ENTRYTYPE", "ID", "title", "author", "year", "doi"):
            assert original_entry[field] == expected[field]
        for field in ("journal", "booktitle", "publisher", "howpublished"):
            if field in expected:
                assert original_entry[field] == expected[field]
            else:
                assert field not in original_entry
        assert parsed_entry["doi"] == expected["doi"]
        assert parsed_entry["query_string"] is None
