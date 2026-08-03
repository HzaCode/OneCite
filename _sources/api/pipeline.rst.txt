Pipeline Processing Reference
==============================

Overview
--------

The OneCite pipeline is a 4-stage process that transforms raw references
into formatted BibTeX or CSL-JSON:

1. **Parse** — read the raw input and produce ``RawEntry`` objects
2. **Identify** — look up each entry in external APIs and fill in a DOI / basic metadata
3. **Enrich** — fetch full metadata for the identified entries
4. **Format** — render the completed entries as BibTeX or CSL-JSON

The implementation lives in the ``src/onecite/pipeline/`` package with one
module per stage.  For backwards-compatibility all public symbols remain
importable from ``onecite.pipeline``:

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

    src/onecite/pipeline/
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

**Purpose:** route supported identifiers into an ``IdentifiedEntry`` with a
DOI / arXiv ID / URL plus basic metadata. Ordinary plain-text title searches
are not resolved by the processing pipeline; use the suggestion workflow for
candidate search. Explicitly labelled thesis/dissertation text is a separate
exception described below.

**Input:** ``List[RawEntry]`` and an ``interactive_callback`` kept for API
compatibility.

**Output:** ``List[IdentifiedEntry]``.

**Data sources actually queried by the code:**

- ``process`` uses input-specific routes: Crossref/DataCite/Zenodo for DOIs,
  NCBI for PMIDs and DOI-based abstract fallback, arXiv for arXiv IDs, Google
  Books for ISBN-bearing references, GitHub for repository URLs, and the host
  supplied by an ordinary URL to inspect publisher-declared DOI metadata.
- Explicit thesis/dissertation text is sent to OpenAIRE and then BASE. If
  neither returns a record, explicit author/title/year/school fields parsed
  from the input can be formatted with an internal ``manual`` source marker.
- ``suggest`` always consults Crossref, Semantic Scholar, and arXiv for a
  usable query. It conditionally adds PubMed, Google Books, OpenAIRE/BASE, and
  the opt-in Google Scholar fallback.

There is **no runtime routing based on filename** and no fixed priority for
"medical", "CS" or "general" queries. Text-only entries in ``process`` are
reported as unresolved rather than guessed, except for the explicit thesis
route above. See :doc:`../external_services` for exact triggers, transmitted
data, privacy boundaries, and source-health limitations.

**Confidence model:**

After all suggestion sources have returned candidates, ``_score_candidates``
assigns each candidate a ``match_score`` (0–100) based on title / author /
year / venue similarity to the query. Scores are returned for human or
downstream review; they are not treated as validation proof.

OneCite does not synthesize missing source fields. Unresolved ordinary entries
are marked ``identification_failed`` rather than filled with guessed metadata;
the thesis exception copies fields that are explicitly present in the user's
input. This is not a guarantee that upstream metadata is correct, complete, or
current. A source can return the wrong work or inaccurate fields, and
source-resolution does not check authenticity or retraction status.

.. code-block:: python

    from onecite.pipeline import IdentifierModule

    identifier = IdentifierModule(use_google_scholar=False)
    identified = identifier.identify(entries)

Stage 3: Enrich (``EnricherModule``)
------------------------------------

**Purpose:** take each ``IdentifiedEntry`` and produce a
``CompletedEntry``. The selected template supplies a fallback entry type and a
declared field set; it does not cause every declared source to be queried.

**Input:** ``List[IdentifiedEntry]`` and the loaded template.

**Output:** ``List[CompletedEntry]``.

**Fields typically filled in:**

- ``author``, ``title``, ``journal`` / ``booktitle``, ``year``
- ``volume``, ``number``, ``pages``, ``publisher``
- ``doi``, ``url``, ``arxiv`` / ``arxiv_id``
- ``abstract`` — returned directly by CrossRef or Semantic Scholar when
  the identification stage resolved the entry through them; otherwise
  filled in by a post-hoc DOI-only cascade described below.

The ``_get_crossref_metadata`` method requests each DOI with a proper
``User-Agent`` header and a ``mailto`` query-string parameter, per
CrossRef's etiquette (fixes #21).

``_complete_fields`` intentionally performs **only one** kind of
completion: abstract back-fill, through a DOI-only cascade

.. code-block:: text

    Semantic Scholar (/paper/DOI:{doi}?fields=abstract)
      ↓  (empty or 4xx)
    PubMed ESearch (DOI → PMID) + EFetch (PMID → abstract)

The cascade is gated by ``allow_abstract_fallback`` and is only invoked
when the caller's **raw input** carried a DOI. A DOI returned by another
route does not trigger it, and ``process`` does not accept fuzzy candidates.
Title-based fallback is intentionally not used anywhere on this path — in
testing it silently returned the abstract of an unrelated paper for at least
one DOI
(``10.1007/s10462-019-09792-7``), which is strictly worse than
returning ``None`` for downstream semantic cross-checks.

Wider template-driven field completion from external scrapers (the
Google Scholar path flagged in review #29) was removed in 0.1.0 and is
**not** being reintroduced here.  The template still controls which
``entry_type`` the formatter falls back to when classification is
ambiguous, and continues to determine the declared field set; as of
this release, the default ``journal_article_full`` template lists
``abstract`` as an optional field so its declaration matches what the
enricher actually emits.

The legacy kwarg name ``allow_pubmed_fallback`` is retained as a
deprecated alias for one release cycle and emits
``DeprecationWarning`` when used — its replacement
``allow_abstract_fallback`` reflects that the flag gates the full
Semantic-Scholar + PubMed cascade, not just PubMed.

Stage 4: Format (``FormatterModule``)
-------------------------------------

**Purpose:** render each ``CompletedEntry`` as a BibTeX or CSL-JSON string.

**Input:** ``List[CompletedEntry]`` and an ``output_format``.

**Output:** a dict with ``results`` (list of formatted strings) and
``report`` (``total`` / ``succeeded`` / ``failed_entries``).

``"bibtex"`` and ``"csl-json"`` are accepted; passing any other value raises
``FormatError``. The previous APA and MLA renderers were removed in
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
        output_format="bibtex"
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
    identified = identifier.identify(raw)
    completed = enricher.enrich(identified, template, raw)
    result = formatter.format(completed, "bibtex")

    print(result['results'])

Error Handling
==============

All pipeline errors inherit from ``OneCiteError``:

- ``ValidationError`` — the high-level call received empty input
- ``ParseError`` — ``ParserModule`` rejected the input type or BibTeX content
- ``ResolverError`` — retained for API compatibility, but ordinary resolution
  misses in the current high-level pipeline are recorded in
  ``report["failed_entries"]`` rather than raised
- ``FormatError`` — the requested ``output_format`` is neither ``"bibtex"``
  nor ``"csl-json"``

Inspect the returned ``failed_entries`` even when no exception was raised. A
reason such as ``no_strong_identifier`` is not a network error; it directs the
entry to ``suggest``. See :doc:`exceptions` for the current exception/report
boundary.

.. code-block:: python

    from onecite import process_references, ValidationError, FormatError

    try:
        result = process_references(
            input_content="",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex"
        )
    except ValidationError:
        print("Empty input")

    try:
        process_references(
            input_content="10.1038/nature14539",
            input_type="txt",
            template_name="journal_article_full",
            output_format="apa",   # no longer supported
        )
    except FormatError as exc:
        print(exc)

Testing Hooks
=============

Because ``src/onecite/pipeline/__init__.py`` imports ``requests`` at the
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
