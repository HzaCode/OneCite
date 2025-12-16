Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_, and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

Added
~~~~~

- Comprehensive RST documentation using Sphinx
- Full API reference documentation
- FAQ section with common questions
- Contributing guidelines
- MCP (Model Context Protocol) integration documentation

Changed
~~~~~~~

- Improved error handling and exception hierarchy
- Enhanced Python API with better type hints
- Updated README with more examples

Fixed
~~~~~

- Various bug fixes in data source integration

[0.0.11] - 2024-10-19
---------------------

Added
~~~~~

- MCP server support for AI assistant integration
- Custom YAML-based template system
- Support for multiple output formats (BibTeX, APA, MLA)
- Interactive mode for ambiguous reference selection
- Support for DOI, arXiv, PMID, ISBN, and GitHub identifiers
- Integration with 9 major academic data sources
- Comprehensive test suite

Changed
~~~~~

- Refactored core processing pipeline
- Improved data source prioritization
- Enhanced error messages

Fixed
~~~~~

- Fixed encoding issues with special characters
- Improved robustness of DOI parsing
- Fixed compatibility with older Python versions

[0.0.10] - 2024-10-01
---------------------

Added
~~~~~

- Initial Python API
- Basic citation processing
- Support for journal articles and conference papers

Changed
~~~~~

- Improved search accuracy

Fixed
~~~~~

- Fixed several data source API issues

[0.0.9] and Earlier
-------------------

See `GitHub Releases <https://github.com/HzaCode/OneCite/releases>`_ for details on older versions.

Upgrade Guide
=============

From 0.0.10 to 0.0.11
---------------------

**Breaking Changes:** None

**New Features:**

- MCP server for AI integration - set up using ``onecite-mcp``
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

**Latest Stable:** 0.0.11

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

- Major releases: Annually or as needed for major features
- Minor releases: Quarterly or as needed
- Patch releases: As needed for critical bugs

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

See `CONTRIBUTORS.md <https://github.com/HzaCode/OneCite/blob/main/CONTRIBUTORS.md>`_ for a full list.

Next Steps
----------

- Check :doc:`quick_start` to get started
- Read :doc:`contributing` to contribute
- See :doc:`faq` for common questions
