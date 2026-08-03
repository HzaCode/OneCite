"""Fail-closed regression tests for malformed or contradictory BibTeX."""

import pytest

from onecite.exceptions import ParseError
from onecite.pipeline.parser import ParserModule


@pytest.mark.parametrize("second_name", ["doi", "DOI"])
def test_duplicate_field_in_one_entry_is_rejected(second_name):
    content = (
        "@article{conflicting,\n"
        "  title={Controlled duplicate-field case},\n"
        "  doi={10.1000/first},\n"
        f"  {second_name}={{10.1000/second}}\n"
        "}\n"
    )

    with pytest.raises(ParseError, match=r"Duplicate BibTeX fields.*conflicting: doi"):
        ParserModule().parse(content, "bib")


def test_same_field_names_across_entries_remain_valid():
    content = (
        "@article{first,\n"
        "  title={First controlled record},\n"
        "  doi={10.1000/first}\n"
        "}\n"
        "@article{second,\n"
        "  title={Second controlled record},\n"
        "  doi={10.1000/second}\n"
        "}\n"
    )

    entries = ParserModule().parse(content, "bib")

    assert [entry["original_entry"]["ID"] for entry in entries] == ["first", "second"]
