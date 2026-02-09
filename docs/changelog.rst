Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_, and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

[0.1.0] - 2025-02-09
---------------------

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

- Refactored exception hierarchy
- Added type hints to Python API
- Updated README examples
- Bumped minimum Python version declaration in docs to 3.10
- Updated CI actions to latest versions (checkout v4, setup-python v5)
- Updated copyright year to 2024-2025
- Fixed Documentation URL in pyproject.toml to point to GitHub Pages

Removed
~~~~~~~

- MCP integration page and all related references
- ``.readthedocs.yml`` (docs now hosted on GitHub Pages)
- ``docs/_build/`` build artifacts from repository

Fixed
~~~~~

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
