Benchmarking
============

OneCite includes a deterministic benchmark runner for local regression checks
and CI workflows. The bundled suite is a small golden-case suite for covered
DOI lookup, arXiv lookup, PMID/PubMed lookup, GitHub software URLs,
Zenodo/DataCite dataset DOIs, and mixed valid/invalid input handling.

The benchmark is intended to catch regressions in covered source-routing,
reporting, and BibTeX-output behavior. It is not a comprehensive citation
accuracy benchmark, a performance benchmark, or a claim that every possible
input or upstream source path is correct.

The repository also includes a baseline run record at
``benchmarks/leaderboard.json``.

Run the bundled benchmark suite::

    onecite benchmark

Use JSON output for automation::

    onecite benchmark --json

By default, the bundled suite uses offline source fixtures so local and CI
checks are reproducible. The offline mode patches OneCite's
HTTP source calls to bundled fixtures and does not require external
network access. Use live APIs only when you are explicitly checking
upstream source behavior::

    onecite benchmark --live --json

Use a custom benchmark suite::

    onecite benchmark --cases my_cases.json --min-success-rate 1.0 --json

Exit Codes
----------

- ``0`` - The benchmark pass rate met the configured pass-rate gate. With
  the default ``--min-success-rate 1.0``, this means every case passed.
- ``1`` - The benchmark pass rate was below the configured pass-rate gate,
  or the suite could not be loaded or run.

Suite Format
------------

Benchmark suites are JSON files with this shape::

    {
      "suite": "my-suite",
      "version": "1.1",
      "cases": [
        {
          "id": "doi-case",
          "input": "10.1038/nature14539",
          "input_type": "txt",
          "template": "journal_article_full",
          "output_format": "bibtex",
          "expect": {
            "min_total": 1,
            "min_succeeded": 1,
            "min_failed": 0,
            "required_substrings": [
              "10.1038/nature14539"
            ]
          }
        }
      ]
    }

Each case runs through the normal OneCite pipeline with interactive
selection disabled. Ambiguous candidates are skipped by default, matching
the non-interactive ``onecite process`` default rather than auto-selecting
the first candidate. The report records per-case failures, observed entry
counts, and the overall gate status.

What a Passing Run Means
------------------------

Passing the bundled benchmark means only that the current implementation
handled the bundled cases and met the configured pass-rate gate. It is useful
as a regression signal because the cases exercise representative source
routes and unresolved-entry reporting, but it should be reported with the
suite name, suite version, source mode, total case count, and pass counts.

For citation-quality assessment beyond this regression suite, use a larger
custom suite with field-level expectations for title, DOI, authors, year,
entry type, URL, and unresolved-entry behavior. Live checks should be treated
as upstream-source spot checks because they can change when external services
change their metadata, availability, or rate limits.

Bundled Coverage
----------------

The default suite is intentionally small enough to run in CI. It is meant to
catch regressions in the covered paths, not to measure overall citation
accuracy. It currently covers:

- Crossref DOI enrichment for journal metadata.
- arXiv identifier lookup for preprint/conference metadata.
- PMID lookup through PubMed identification and DOI enrichment.
- GitHub repository URLs as software citations.
- Zenodo and DataCite DOI paths as dataset citations.
- Mixed valid/invalid batches where unresolved entries must be reported.
