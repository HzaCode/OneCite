"""Cite-key generation must always yield LaTeX-safe ASCII keys.

Keys end up inside ``\\cite{...}``: accented characters are folded, CJK is
dropped, and an integer year (as delivered by DataCite's
``publicationYear``) must not crash the generator.
"""

from onecite.pipeline.enricher import EnricherModule


def _key(metadata):
    return EnricherModule()._generate_bibtex_key(metadata)


def test_integer_year_does_not_crash():
    key = _key({"title": "Data set", "author": "Dryad Data Repository", "year": 2021})
    assert key == "Repository2021Data"


def test_accented_names_are_ascii_folded():
    assert _key({"title": "Étude générale", "author": "Müller, Hans", "year": 2019}) == (
        "Muller2019Etude"
    )


def test_cjk_only_parts_are_dropped_not_emitted():
    key = _key({"title": "深度学习综述", "author": "谢三", "year": 2020})
    assert key.isascii()
    assert key  # never empty


def test_apostrophes_removed():
    assert _key({"title": "Attention", "author": "O'Neil, K.", "year": "2017"}) == (
        "ONeil2017Attention"
    )


def test_all_empty_falls_back_to_unknown():
    assert _key({}) == "unknown"
