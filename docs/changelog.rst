Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_, and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

[0.1.0] - 2026-04-17
---------------------

First formal PyPI release since ``0.0.12``.  Incorporates the complete
pyOpenSci review pass (issues #3, #5–#34, #36) plus follow-up cleanup.
See ``CHANGELOG.md`` at the repository root for the full per-issue list.

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
  ``onecite/pipeline/`` package with one module per stage (#17)
- Unify CrossRef request and parsing methods, with ``User-Agent`` and
  ``mailto`` set per CrossRef etiquette (#21, #26)
- Rewrite fuzzy-search scoring as a weighted title/author/year/venue
  model with three confidence tiers (#3, #23, #27)
- Simplify identifier routing; CrossRef and Semantic Scholar are the
  always-on sources, with signal-based PubMed / Google Books /
  external providerRE / BASE queries (#8, #23)
- Use ``bibtexparser.dumps()`` for BibTeX rendering (#30)
- Expose ``use_google_scholar`` as a real CLI flag and API parameter (#10)
- Clarify that templates define metadata-field requirements and a
  fallback BibTeX entry type, not output formatting (#16, #29)
- Refactored exception hierarchy
- Added type hints to Python API

Removed
~~~~~~~

- APA and MLA output renderers; the CLI now rejects anything other than
  ``--output-format bibtex``.  Use pandoc or citeproc-py to convert the
  generated BibTeX to APA / MLA (#31, #32)
- Hard-coded "well-known paper" shortcut that masked failures on the
  main example input (#19)
- MCP integration page and all related references
- ``.readthedocs.yml`` (docs now hosted on GitHub Pages)
- ``docs/_build/`` build artifacts from repository

Fixed
~~~~~

- OpenAlex and dblp no longer listed as data sources — they were never
  wired into the code (#6)
- ``docs/api/pipeline.rst`` rewritten to match the real modules;
  removed references to nonexistent classes / methods (#11)
- README and docs ``@inproceedings`` example now uses ``booktitle``
  instead of ``journal = "arXiv preprint"`` (#28)
- Crossref author names parsed as ``given family`` (#22)
- Semantic Scholar HTTP 429 handled cleanly (#25)
- Previously-unused exception classes now raised in the right places
  (#13)
- ``CONTRIBUTING.md`` documents ``pip install -e .[dev]`` instead of
  the non-existent ``requirements.txt`` (#12)
- URL-bearing entries no longer queried twice (#20)
- Fallback paths mark entries as ``identification_failed`` rather than
  fabricating invented metadata (#24)
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

Planned Features
================

**Version 0.1.0 (Planned)**

- Web interface at hezhiang.com/onecite
- Support for more citation formats (Chicago, IEEE, etc.)
- Citation deduplication tools
- Bibliography merging utilities
- Advanced search filters

**Version 0.2.0 (Planned)**

- Database support for storing citations
- Collaborative features
- Export to popular reference managers (Zotero, Mendeley)
- Advanced batch processing

**Future Roadmap**

- Machine learning-based citation quality assessment
- Automatic citation error detection
- Citation trend analysis
- Integration with more academic platforms

Version History
===============

**Latest Stable:** 0.1.0

**Python Support:**

- 3.10+
- 3.11+

**Requirements:**

See ``requirements.txt`` for current dependencies.

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
