# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-04-17

First formal PyPI release since `0.0.12`.  Incorporates the complete
pyOpenSci review pass (issues #3, #5–#34, #36) plus follow-up cleanup.

### Added
- RST documentation using Sphinx
- Full API reference documentation
- FAQ section with common questions
- Contributing guidelines
- Pre-commit hooks configuration
- Google-style docstrings with Args/Returns for all public API functions
- Auto-deploy documentation to GitHub Pages via CI

### Changed
- **Split monolithic `pipeline.py` (~3000 lines)** into a proper
  `onecite/pipeline/` package with one module per stage
  (`parser.py` / `identifier.py` / `enricher.py` / `formatter.py`)
  plus a `_utils.py` for shared helpers (#17).  Public imports
  (`from onecite.pipeline import IdentifierModule`) and mocking targets
  (`patch("onecite.pipeline.requests.get", ...)`) continue to work
  unchanged because `__init__.py` re-exports every public symbol and
  keeps `requests` at the package level.
- Unify CrossRef request and parsing methods (#26); all CrossRef calls
  now go through a single helper with a proper `User-Agent` header and
  `mailto` query-string parameter (#21).
- Rewrite fuzzy-search scoring as a weighted title / author / year /
  venue model with three confidence tiers (auto-adopt / interactive /
  cautious) and a unified low-confidence threshold (#3, #23, #27).
- Simplify identifier routing; CrossRef and Semantic Scholar are always
  consulted for text queries, with signal-based additional queries to
  PubMed / Google Books / external providerRE / BASE (#8, #23).
- Use `bibtexparser.dumps()` for BibTeX rendering (#30).
- Expose `use_google_scholar` as a real CLI flag and API parameter
  instead of a hard-coded `False` (#10).
- Clarify that templates define metadata-field requirements and a
  fallback BibTeX entry type, not output formatting (#16, #29).
- Refactored exception hierarchy
- Added type hints to Python API
- Updated README examples
- Bumped minimum Python version declaration in docs to 3.10
- Updated CI actions to latest versions (checkout v4, setup-python v5)
- Updated copyright year to 2024-2025
- Fixed Documentation URL in pyproject.toml to point to GitHub Pages

### Removed
- APA and MLA output renderers; they produced inconsistent output and
  the CLI now rejects anything other than `--output-format bibtex`.
  Users wanting APA/MLA should post-process the BibTeX through pandoc
  or citeproc-py (#31, #32).
- Hard-coded "well-known paper" shortcut that masked failures on the
  main example input (#19).
- MCP integration page and all related references
- `.readthedocs.yml` (docs now hosted on GitHub Pages)
- `docs/_build/` build artifacts from repository

### Fixed
- README / `docs/index.rst` / `docs/faq.rst` no longer advertise
  OpenAlex or dblp as data sources — they were never wired into the
  code (#6).
- README quick-start example now shows `booktitle` (NeurIPS) instead
  of `journal = "arXiv preprint"` for the `@inproceedings` sample
  (#28).
- `docs/api/pipeline.rst` rewritten to match the actual module
  structure; removed references to classes and methods that never
  existed (`Validator` / `Identifier` / `Completer` / `Formatter`,
  `set_source_priority`, `set_timeout`, `add_template_path`) (#11).
- `docs/output_formats.rst`, `docs/faq.rst`, `docs/quick_start.rst`,
  `docs/python_api.rst`, `docs/templates.rst`, `docs/index.rst` and
  docstrings in `core.py` / `formatter.py` no longer advertise APA /
  MLA output (#31, #32).
- Crossref author names parsed as `given family` instead of mangled
  concatenations (#22).
- Semantic Scholar HTTP 429 responses return an empty candidate list
  cleanly instead of bubbling up (#25).
- Previously-unused exception classes (`ParseError`, `ValidationError`,
  `FormatError`) are now actually raised in the right places (#13).
- `CONTRIBUTING.md` no longer tells developers to use a `requirements.txt`
  that does not exist; the documented install is `pip install -e .[dev]`
  (#12).
- `black` formatting is enforced via `pyproject.toml` `[tool.black]`
  plus a pre-commit hook (#15).
- URL-bearing entries are no longer queried twice (#20).
- Fallback paths mark entries as `identification_failed` rather than
  fabricating plausible-looking but invented metadata (#24).
- CrossRef and Semantic Scholar response parsing edge cases
- API documentation using incorrect return value fields (`output_content` -> `results`)
- Version number inconsistencies across metadata files
- Python version requirement inconsistencies in docs (3.7 -> 3.10)

## [0.0.11] - 2024-10-19

### Added
- Custom YAML-based template system
- Support for multiple output formats (BibTeX, APA, MLA)
- Interactive mode for ambiguous reference selection
- Support for DOI, arXiv, PMID, ISBN, and GitHub identifiers
- Integration with 9 major academic data sources
- Test suite

### Changed
- Refactored core processing pipeline
- Reordered data source priority (CrossRef first for DOI queries)
- Clearer error messages on failed lookups

### Fixed
- Encoding issues with non-ASCII characters in author names
- DOI parsing for URLs with trailing query strings
- Python 3.10 compatibility issues

## [0.0.10] - 2024-10-01

### Added
- Initial Python API
- Basic citation processing
- Support for journal articles and conference papers

### Changed
- Better title matching for fuzzy searches

### Fixed
- PubMed API response handling
- Semantic Scholar rate limit handling

## [0.0.9] and Earlier

See [GitHub Releases](https://github.com/HzaCode/OneCite/releases) for details on older versions.
