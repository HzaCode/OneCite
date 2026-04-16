Pipeline Processing Reference
==============================

Overview
--------

The OneCite pipeline is a 4-stage process that transforms raw references
into formatted BibTeX:

1. **Parse** — read the raw input and produce ``RawEntry`` objects
2. **Identify** — look up each entry in external APIs and fill in a DOI / basic metadata
3. **Enrich** — fetch full metadata for the identified entries
4. **Format** — render the completed entries as BibTeX

Since pyOpenSci review issue #17, the implementation lives in the
``onecite/pipeline/`` package with one module per stage.  For
backwards-compatibility all public symbols remain importable from
``onecite.pipeline``:

.. code-block:: python

    from onecite.pipeline import (
        ParserModule,
        IdentifierModule,
        EnricherModule,
        FormatterModule,
    )

Package Layout
--------------

.. code-block:: text

    onecite/pipeline/
        __init__.py     - re-exports + ``requests`` at package level
        _utils.py       - _safe_year helper
        parser.py       - ParserModule
        identifier.py   - IdentifierModule
        enricher.py     - EnricherModule
        formatter.py    - FormatterModule

Pipeline Stages
===============

Stage 1: Parse (``ParserModule``)
---------------------------------

**Purpose:** split the input into one ``RawEntry`` per reference.

**Input:** the raw ``input_content`` string and an ``input_type``
(``"txt"`` or ``"bib"``).

**Output:** ``List[RawEntry]``.

``ParserModule.parse(input_content, input_type)`` dispatches to
``_parse_bibtex`` or ``_parse_text``.  The text parser splits on blank
lines (one reference per block), extracts any DOI or URL found in the
block, and builds a ``query_string`` for later identification when no
identifier is present.

.. code-block:: python

    from onecite.pipeline import ParserModule

    parser = ParserModule()
    entries = parser.parse("10.1038/nature14539\n\n1706.03762", "txt")
    # [{'id': 0, 'raw_text': '10.1038/nature14539', 'doi': '10.1038/nature14539', ...},
    #  {'id': 1, 'raw_text': '1706.03762', ...}]

``ParseError`` is raised when the input type is unsupported or BibTeX
parsing fails.

Stage 2: Identify (``IdentifierModule``)
----------------------------------------

**Purpose:** resolve each ``RawEntry`` against academic data sources and
produce an ``IdentifiedEntry`` with a DOI (when possible) plus basic
metadata.

**Input:** ``List[RawEntry]`` and an ``interactive_callback`` that picks
from candidate lists when confidence is medium.

**Output:** ``List[IdentifiedEntry]``.

**Data sources actually queried by the code:**

- CrossRef (DOI-based and fuzzy search)
- Semantic Scholar (keyword search)
- arXiv (via feedparser)
- PubMed (biomedical, queried when strong cues are present)
- DataCite / Zenodo (datasets)
- Google Books (books — triggered by ISBN or publisher cues)
- external providerRE / BASE (theses)
- GitHub (software repositories)
- Google Scholar (optional, disabled by default; opt-in via
  ``--google-scholar`` or ``use_google_scholar=True`` and requires the
  ``scholarly`` package)

There is **no runtime routing based on filename** and no fixed priority
for "medical", "CS" or "general" queries.  Signal-based heuristics
inside ``_fuzzy_search`` decide when to *additionally* query PubMed,
Google Books, external providerRE/BASE, etc., but CrossRef and Semantic Scholar are
always consulted for text queries.

**Confidence model:**

After all sources have returned candidates, ``_score_candidates`` assigns
each candidate a ``match_score`` (0–100) based on title / author /
year / venue similarity to the query.  The decision logic in
``_fuzzy_search`` then chooses one of three paths:

- ``match_score >= 80`` and a clear best candidate → auto-adopt
- ``70 <= match_score < 80`` → call the ``interactive_callback`` with up
  to 5 candidates; fall back to the top candidate if the user skips and
  the score is still ≥ 75
- ``match_score >= 50`` and a title is present → adopt cautiously
- otherwise → mark the entry as ``identification_failed``

This matches what the pyOpenSci review flagged in issues #3, #23 and
#27.  Fallbacks never fabricate data (see #24).

.. code-block:: python

    from onecite.pipeline import IdentifierModule

    identifier = IdentifierModule(use_google_scholar=False)
    identified = identifier.identify(entries, interactive_callback=lambda c: 0)

Stage 3: Enrich (``EnricherModule``)
------------------------------------

**Purpose:** take each ``IdentifiedEntry`` and produce a
``CompletedEntry`` with the BibTeX fields the selected template
requires.

**Input:** ``List[IdentifiedEntry]`` and the loaded template.

**Output:** ``List[CompletedEntry]``.

**Fields typically filled in:**

- ``author``, ``title``, ``journal`` / ``booktitle``, ``year``
- ``volume``, ``number``, ``pages``, ``publisher``
- ``doi``, ``url``, ``arxiv`` / ``arxiv_id``
- ``abstract`` (from CrossRef when available, otherwise from PubMed's
  ``EFetch`` endpoint when the entry has a resolvable PMID)

The ``_get_crossref_metadata`` method requests each DOI with a proper
``User-Agent`` header and a ``mailto`` query-string parameter, per
CrossRef's etiquette (fixes #21).

``_complete_fields`` is intentionally a no-op pass-through:
template-driven field completion from external scrapers was removed
(see #16, #29).  The template now only affects which ``entry_type`` the
formatter falls back to when classification is ambiguous.

Stage 4: Format (``FormatterModule``)
-------------------------------------

**Purpose:** render each ``CompletedEntry`` as a BibTeX string.

**Input:** ``List[CompletedEntry]`` and an ``output_format``.

**Output:** a dict with ``results`` (list of formatted strings) and
``report`` (``total`` / ``succeeded`` / ``failed_entries``).

Only ``"bibtex"`` is accepted; passing any other value raises
``FormatError``.  The previous APA and MLA renderers were removed in
response to issues #31 and #32; for APA / MLA output, post-process the
BibTeX file with pandoc or citeproc-py.

Rendering uses :mod:`bibtexparser` (``bibtexparser.dumps``) so the
output complies with the BibTeX grammar; LaTeX-special characters in
``author``, ``title``, ``journal``, ``publisher``, etc. are escaped
unless the field already contains explicit LaTeX commands
(e.g. ``K{\\"u}nsch``).

Complete Pipeline
=================

Most callers never touch the individual modules and instead use the
high-level ``process_references`` function:

.. code-block:: python

    from onecite import process_references

    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0,  # auto-pick first
    )

    print('\n\n'.join(result['results']))
    print(result['report'])

Under the hood this creates a :class:`PipelineController` and calls its
``process`` method, which runs all four stages in order.

Running Stages Manually
-----------------------

For advanced uses (e.g. unit-testing a single stage) you can drive the
modules directly:

.. code-block:: python

    from onecite import TemplateLoader
    from onecite.pipeline import (
        ParserModule,
        IdentifierModule,
        EnricherModule,
        FormatterModule,
    )

    template = TemplateLoader().load_template("journal_article_full")

    parser = ParserModule()
    identifier = IdentifierModule(use_google_scholar=False)
    enricher = EnricherModule(use_google_scholar=False)
    formatter = FormatterModule()

    raw = parser.parse("10.1038/nature14539", "txt")
    identified = identifier.identify(raw, interactive_callback=lambda c: 0)
    completed = enricher.enrich(identified, template, raw)
    result = formatter.format(completed, "bibtex")

    print(result['results'])

Error Handling
==============

All pipeline errors inherit from ``OneCiteError``:

- ``ValidationError`` — empty / malformed input
- ``ParseError`` — ``ParserModule`` could not split the input
- ``ResolverError`` — raised by helpers when a data source cannot
  resolve an identifier; generally caught internally and recorded as
  ``identification_failed`` on the entry instead of propagating
- ``FormatError`` — the requested ``output_format`` is not ``"bibtex"``

.. code-block:: python

    from onecite import process_references, ValidationError, FormatError

    try:
        result = process_references(
            input_content="",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda c: 0,
        )
    except ValidationError:
        print("Empty input")

    try:
        process_references(
            input_content="10.1038/nature14539",
            input_type="txt",
            template_name="journal_article_full",
            output_format="apa",   # no longer supported
            interactive_callback=lambda c: 0,
        )
    except FormatError as exc:
        print(exc)

Testing Hooks
=============

Because ``onecite/pipeline/__init__.py`` imports ``requests`` at the
package level, tests that mock the network can continue to use the
original patch target:

.. code-block:: python

    from unittest.mock import patch

    with patch("onecite.pipeline.requests.get", side_effect=fake_get):
        ...

For mocking the optional ``scholarly`` dependency, patch the concrete
submodule attribute instead — ``scholarly`` is imported inside
``identifier.py`` and ``enricher.py``:

.. code-block:: python

    import onecite.pipeline.identifier as identifier_mod
    with patch.object(identifier_mod, "scholarly", fake_scholarly):
        ...

Next Steps
----------

- See :doc:`../python_api` for usage examples
- Check :doc:`../api/core` for the data-class and public-function
  reference
- Review :doc:`../advanced_usage` for real-world workflows
