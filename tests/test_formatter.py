from onecite.pipeline.formatter import FormatterModule


def test_escape_latex_chars_maps_curly_quotes():
    formatter = FormatterModule()

    assert formatter._escape_latex_chars("“Deep Learning” and ‘quotes’") == (
        "``Deep Learning'' and `quotes'"
    )


def test_escape_latex_chars_preserves_existing_latex_commands():
    formatter = FormatterModule()

    assert formatter._escape_latex_chars(r"K{\"u}nsch") == r"K{\"u}nsch"


def test_bibtex_formatter_escapes_unicode_quotes_in_text_fields():
    formatter = FormatterModule()
    entry = {
        "id": 1,
        "status": "completed",
        "bib_key": "Quote2026",
        "bib_data": {
            "ENTRYTYPE": "article",
            "ID": "Quote2026",
            "title": "“Reliable” references",
            "author": "Author, Test",
            "year": "2026",
        },
    }

    result = formatter.format([entry], "bibtex")

    assert result["report"]["succeeded"] == 1
    assert "``Reliable'' references" in result["results"][0]
