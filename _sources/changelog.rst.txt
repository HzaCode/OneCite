Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_, and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

Added
~~~~~

- Enhanced CLI modes for automated workflows: ``onecite process --json``,
  ``onecite process --ndjson``, and ``--fail-on-unresolved`` exit code
  ``2`` for unresolved-entry handling in scripts.
- ``onecite benchmark`` CLI command with bundled deterministic golden
  cases, JSON output, and a configurable pass-rate gate for covered
  regression cases, plus a repository baseline record
  at ``benchmarks/leaderboard.json``.
- Expanded the bundled benchmark suite to cover PMID/PubMed lookup,
  GitHub software URLs, Zenodo/DataCite dataset DOIs, and more explicit
  benchmark-suite schema validation.
- ``onecite doctor`` CLI command with stable JSON output for package,
  template, benchmark-resource, skill-package, and offline benchmark
  health checks.
- CLI contract documentation for JSON/NDJSON process reports, benchmark
  reports, doctor reports, stdout/stderr behavior, and exit codes.
- Repository-contained OneCite Skill package at
  ``skills/onecite/SKILL.md`` with metadata-lookup and local verification
  operating instructions.
- ``onecite templates`` CLI command for listing bundled fallback BibTeX
  templates, including machine-readable ``--json`` output for tools
  that need to inspect available presets.

Changed
~~~~~~~

- Default pytest runs now exclude live external-API checks;
  live checks are explicitly marked with ``pytest.mark.live`` so the
  default suite is deterministic and offline.

Fixed
~~~~~

- Corrected the benchmark Nature DQN DOI fixture from
  ``10.1038/nature14539`` to ``10.1038/nature14236``, and added
  regression coverage to catch future DOI-title-author mismatches in
  bundled golden cases.
- Added benchmark expectation checks for expected failed entries so
  mixed valid/invalid cases must exercise unresolved-entry reporting.
- Added the documented ``onecite version`` subcommand alongside
  ``onecite --version``.
- Fixed LaTeX formatting for curly single and double quotes.
- Blocked live CrossRef/Semantic Scholar calls in fuzzy-search unit
  tests unless a test opts into a mocked source explicitly.
- Kept machine-readable JSON/NDJSON stdout clean when ``--output`` is
  used by routing the saved-file status message to stderr.
- Included the OneCite Skill and benchmark baseline files in built
  distribution artifacts.
- Added benchmark and doctor checks to the GitHub Actions test
  workflow.

[0.1.1] - 2026-04-17
---------------------

Maintenance release focused on **aligning the abstract-retrieval
semantics across code, templates, docs, tests, and metadata**.  No
breaking public-API changes; the one renamed kwarg keeps its old name
as a deprecated alias for this release cycle.

Added
~~~~~

- Abstract retrieval now falls back through a DOI-only cascade when
  CrossRef does not return an abstract: Semantic Scholar
  (``/paper/DOI:{doi}?fields=abstract``) → PubMed (ESearch DOI→PMID,
  then EFetch PMID→abstract).  The cascade is only invoked when the
  user's **original raw input** carried a DOI; DOIs inferred by fuzzy
  search do not trigger it, so a possibly-wrong candidate does not cost
  extra roundtrips.  In particular, a local BibTeX entry with no
  ``doi`` field — regardless of whether other stages would later
  resolve one — does not trigger the abstract cascade.
- Semantic Scholar search results now carry the ``abstract`` field,
  which propagates through ``_convert_search_metadata`` into the final
  BibTeX output whenever the identification stage already resolved the
  entry through SS.
- ``EnricherModule._get_semantic_scholar_abstract(doi)`` helper for
  DOI-based Semantic Scholar abstract retrieval.  Handles ``404`` /
  ``429`` gracefully by returning ``None``.
- ``_complete_fields`` gained an ``allow_abstract_fallback`` kwarg
  (default ``False``) that gates the new cascade.
  ``_enrich_single_entry`` passes ``True`` only when the raw entry
  contributed a DOI.
- Default ``journal_article_full`` template now lists ``abstract`` as
  an optional field so the declaration matches what the enricher
  emits.  The older ``journal_article_with_abstract`` template is
  retained as a compatibility alias and will stay available for at
  least one release cycle.
- Regression test ``test_enrich_single_entry_no_doi_in_raw_skips_abstract_fallback``
  pinning the "no-DOI-in raw ⇒ no Semantic-Scholar/PubMed network
  call" guarantee at the ``_enrich_single_entry`` layer.

Changed
~~~~~~~

- ``_get_pubmed_abstract`` now requires a DOI and no longer falls back
  to PubMed title search.  The removed title-based path empirically
  returned the abstract of an unrelated paper (e.g. a Zhang 2020 example
  Review DOI ``10.1007/s10462-019-09792-7`` pulled the abstract of a
  different RSI segmentation paper), which is strictly worse than
  returning ``None`` for downstream semantic cross-checks such as the
  ``sci`` skill.
- Abstract coverage on an internal 10-DOI cross-publisher spot-check
  rose from 4/9 to 8/9.  This number is a local indicator, **not** a
  release gate: reproducing it requires a live network and the probe
  scripts are no longer in the repository.

Deprecated
~~~~~~~~~~

- ``_complete_fields(..., allow_pubmed_fallback=...)`` is deprecated in
  favour of ``allow_abstract_fallback``.  The old name still works for
  one release cycle and emits ``DeprecationWarning``.  It was renamed
  because the flag actually gates the entire Semantic-Scholar + PubMed
  cascade, not PubMed alone.

Removed
~~~~~~~

- ``IdentifierModule._check_doi_content_consistency`` and the
  ``consistency_score`` / ``low_consistency`` warning path.  A fuzzy
  string-similarity score on bibliographic fields is not a reliable
  signal for detecting fabricated references, and it was only emitted
  as a ``logger.warning`` that downstream tools could not act on.
  Citation-authenticity verification belongs at the abstract-vs-claim
  semantic layer in the consuming tool, not at the bibliographic-string
  layer here.

[0.1.0] - 2026-04-17
---------------------

First formal PyPI release since ``0.0.12``.

Added
~~~~~

- RST documentation using Sphinx
- Full API reference documentation
- FAQ section with common questions
- Contributing guidelines
- Pre-commit hooks configuration
- Google-style docstrings with Args/Returns for all public API functions
- Auto-deploy documentation to GitHub Pages via CI

Changed
~~~~~~~

- **Split monolithic pipeline.py (~3000 lines)** into a proper
  ``onecite/pipeline/`` package with one module per stage
- Unify CrossRef request and parsing methods, with ``User-Agent`` and
  ``mailto`` set per CrossRef etiquette
- Rewrite fuzzy-search scoring as a weighted title/author/year/venue
  model with three confidence tiers
- Simplify identifier routing; CrossRef and Semantic Scholar are the
  always-on sources, with signal-based PubMed / Google Books /
  external providerRE / BASE queries
- Use ``bibtexparser.dumps()`` for BibTeX rendering
- Expose ``use_google_scholar`` as a real CLI flag and API parameter
- Clarify that templates define metadata-field requirements and a
  fallback BibTeX entry type, not output formatting
- Refactored exception hierarchy
- Added type hints to Python API

Removed
~~~~~~~

- APA and MLA output renderers; the CLI now rejects anything other than
  ``--output-format bibtex``.  Use pandoc or citeproc-py to convert the
  generated BibTeX to APA / MLA
- Hard-coded "well-known paper" shortcut that masked failures on the
  main example input
- MCP integration page and all related references
- ``.readthedocs.yml`` (docs now hosted on GitHub Pages)
- ``docs/_build/`` build artifacts from repository

Fixed
~~~~~

- OpenAlex and dblp no longer listed as data sources — they were never
  wired into the code
- ``docs/api/pipeline.rst`` rewritten to match the real modules;
  removed references to nonexistent classes / methods
- README and docs ``@inproceedings`` example now uses ``booktitle``
  instead of ``journal = "arXiv preprint"``
- Crossref author names parsed as ``given family``
- Semantic Scholar HTTP 429 handled cleanly
- Previously-unused exception classes now raised in the right places
- ``CONTRIBUTING.md`` documents ``pip install -e .[dev]`` instead of
  the non-existent ``requirements.txt``
- URL-bearing entries no longer queried twice
- Fallback paths mark entries as ``identification_failed`` rather than
  fabricating invented metadata
- CrossRef and Semantic Scholar response parsing edge cases
- API documentation using incorrect return value fields
- Version number inconsistencies across metadata files
- Python version requirement inconsistencies in docs (3.7 -> 3.10)

[0.0.11] - 2024-10-19
---------------------

Added
~~~~~

- Custom YAML-based template system
- Support for multiple output formats (BibTeX, APA, MLA)
- Interactive mode for ambiguous reference selection
- Support for DOI, arXiv, PMID, ISBN, and GitHub identifiers
- Integration with 9 major academic data sources
- Test suite

Changed
~~~~~

- Refactored core processing pipeline
- Reordered data source priority (CrossRef first for DOI queries)
- Clearer error messages on failed lookups

Fixed
~~~~~

- Encoding issues with non-ASCII characters in author names
- DOI parsing for URLs with trailing query strings
- Python 3.10 compatibility issues

[0.0.10] - 2024-10-01
---------------------

Added
~~~~~

- Initial Python API
- Basic citation processing
- Support for journal articles and conference papers

Changed
~~~~~

- Better title matching for fuzzy searches

Fixed
~~~~~

- PubMed API response handling
- Semantic Scholar rate limit handling

[0.0.9] and Earlier
-------------------

See `GitHub Releases <https://github.com/HzaCode/OneCite/releases>`_ for details on older versions.

Upgrade Guide
=============

From 0.0.10 to 0.0.11
---------------------

**Breaking Changes:** None

**New Features:**

- Custom template support - create YAML templates for custom formats
- APA and MLA formats - use ``--output-format apa`` or ``--output-format mla``
- Interactive mode - use ``--interactive`` flag for ambiguous references

**Migration:**

No migration needed. All existing functionality is backward compatible. New features are opt-in.

Version History
===============

**Latest Stable:** 0.1.1

**Python Support:**

- 3.10+
- 3.11+

**Requirements:**

See ``pyproject.toml`` for current dependencies.

Getting Help
============

- Check :doc:`faq` for common issues
- Search `GitHub Issues <https://github.com/HzaCode/OneCite/issues>`_
- Ask in `GitHub Discussions <https://github.com/HzaCode/OneCite/discussions>`_
- See :doc:`contributing` to report bugs or suggest features

Release Strategy
================

**Versioning:**

OneCite follows `Semantic Versioning <https://semver.org/>`_:

- MAJOR.MINOR.PATCH
- MAJOR: Breaking API changes
- MINOR: New backward-compatible features
- PATCH: Bug fixes

**Release Cadence:**

- Major releases: Annually or for major features
- Minor releases: Quarterly
- Patch releases: For critical bugs

**Support:**

- Latest version: Full support
- Previous major version: Limited support
- Older versions: Community support only

Deprecation Policy
------------------

Features marked as deprecated will:

1. Be announced in release notes
2. Work for at least one minor version
3. Be removed in the next major version

Breaking Changes Policy
-----------------------

Breaking changes are:

1. Announced in advance
2. Clearly documented
3. Provided with migration guide
4. Only released in major versions

Credits
=======

Contributors and acknowledgments:

- OneCite Team
- Open source community
- Data source providers (CrossRef, PubMed, arXiv, etc.)
- All contributors on GitHub

See the `GitHub Contributors page <https://github.com/HzaCode/OneCite/graphs/contributors>`_ for a full list.

Next Steps
----------

- Check :doc:`quick_start` to get started
- Read :doc:`contributing` to contribute
- See :doc:`faq` for common questions
