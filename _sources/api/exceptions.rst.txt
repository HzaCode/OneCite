Exceptions and Per-Entry Failures
=================================

Overview
--------

OneCite defines custom exceptions for invalid calls and malformed input. Normal
identifier-resolution failure is different: the high-level processing pipeline
usually records it in ``report["failed_entries"]`` and continues instead of
raising an exception.

Exception hierarchy
~~~~~~~~~~~~~~~~~~~

::

    Exception
    └── OneCiteError
        ├── ValidationError
        ├── ParseError
        ├── ResolverError
        ├── FormatError
        ├── DataImportError
        └── ExportError

``OneCiteError``
----------------

Base class for OneCite's custom exceptions. Catch it only after the more
specific exception types relevant to the call.

``ValidationError``
-------------------

The public ``process_references`` and ``suggest_references`` functions raise
``ValidationError`` when ``input_content`` is empty or whitespace-only.

.. code-block:: python

    from onecite import process_references, ValidationError

    try:
        process_references(
            input_content="",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
        )
    except ValidationError as exc:
        print(f"Invalid call: {exc}")

A syntactically plausible but nonexistent DOI is not an exception at this
level. It is a per-entry failure such as ``doi_not_found``.

``ParseError``
--------------

``ParseError`` is raised when the parser cannot interpret the requested input
type. Current examples include an unsupported ``input_type`` and malformed,
empty, or duplicate-field BibTeX input.

.. code-block:: python

    from onecite import ParseError, process_references

    try:
        process_references(
            input_content="@article{broken syntax",
            input_type="bib",
            template_name="journal_article_full",
            output_format="bibtex",
        )
    except ParseError as exc:
        print(f"Could not parse BibTeX: {exc}")

``FormatError``
---------------

The formatter raises ``FormatError`` for an unsupported output format or a
serialization failure. The command-line parser rejects unsupported choices
before the pipeline; the Python API exposes the exception directly.

.. code-block:: python

    from onecite import FormatError, process_references

    try:
        process_references(
            input_content="10.1038/nature14539",
            input_type="txt",
            template_name="journal_article_full",
            output_format="apa",  # supported values: bibtex, csl-json
        )
    except FormatError as exc:
        print(f"Unsupported output: {exc}")

``ResolverError``
-----------------

``ResolverError`` remains part of the public exception hierarchy, but the
current ``process_references`` path does not raise it for ordinary lookup
misses, unavailable sources, ambiguous references, or rate limiting. Those
conditions are caught within the pipeline and returned as per-entry failures.
Do not write code that relies on catching ``ResolverError`` to detect an
unresolved citation.

``DataImportError`` and ``ExportError``
---------------------------------------

These exception types remain available for API compatibility. The current
``process_references`` / ``suggest_references`` paths do not raise them.

Inspecting resolution failures
------------------------------

Inspect the returned report even when the function call itself succeeded:

.. code-block:: python

    from onecite import OneCiteError, process_references

    def process_safely(content: str):
        try:
            result = process_references(
                input_content=content,
                input_type="txt",
                template_name="journal_article_full",
                output_format="bibtex",
            )
        except OneCiteError as exc:
            return {"call_error": str(exc), "result": None}

        return {
            "call_error": None,
            "result": result,
            "failed_entries": result["report"]["failed_entries"],
            "warnings": result["report"]["warnings"],
        }

Important per-entry reason codes include:

- ``doi_not_found`` — Crossref returned ``404`` and the DataCite fallback did
  not return a record. The current fallback does not distinguish every DataCite
  miss from every caught DataCite request error, so this reason alone is not
  definitive proof that the DOI does not exist;
- ``source_error`` — Crossref verification failed outside the ``404`` fallback
  path or returned an inconsistent DOI identity;
- ``no_strong_identifier`` — ordinary ambiguous text belongs in ``suggest``;
- ``pmid_unresolved`` or ``isbn_unresolved`` — that identifier route returned
  no usable record; these routes also collapse some provider errors into the
  same reason; and
- ``metadata_unavailable`` / ``enrichment_error`` — identification succeeded
  but enrichment did not produce a completed record.

The reason taxonomy is operational evidence, not a complete provider trace.
For network/privacy behavior and ``suggest`` source-health coverage, see
:doc:`../external_services`.

Batch handling
--------------

One call can contain multiple blank-line-separated entries. The pipeline keeps
completed results and reports unresolved entries in the same response. At the
CLI, combine ``--json`` with ``--fail-on-unresolved`` when automation needs
both the report and exit code ``2`` for a partial failure.

Best practices
--------------

1. Catch ``ValidationError``, ``ParseError``, and ``FormatError`` for invalid
   calls or malformed input.
2. Always inspect ``failed_entries`` and ``warnings`` after a successful call.
3. Treat ``source_error`` as potentially retryable, but do not assume every
   other reason is a network problem.
4. Use ``suggest`` for ordinary title/author queries; do not retry them through
   ``process`` expecting fuzzy acceptance.
5. Follow provider guidance before retrying throttled bulk jobs.

Next steps
----------

- See :doc:`core` for the function signatures.
- Check :doc:`../python_api` for usage examples.
- Review :doc:`../external_services` for external-service boundaries.
