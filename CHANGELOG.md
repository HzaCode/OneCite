# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-04-17

Maintenance release focused on **aligning the abstract-retrieval
semantics across code, templates, docs, tests, and metadata**. No
breaking public-API changes; the one renamed kwarg keeps its old name
as a deprecated alias for this release cycle.

### Added
- Abstract retrieval now falls back through a DOI-only cascade when
  CrossRef does not return an abstract:
  Semantic Scholar (`/paper/DOI:{doi}?fields=abstract`) → PubMed
  (ESearch DOI→PMID, then EFetch PMID→abstract). The cascade is only
  invoked when the user's **original raw input** carried a DOI; DOIs
  inferred by fuzzy search do not trigger it, so that a possibly-wrong
  candidate does not cost extra roundtrips. In particular, a local
  BibTeX entry with no DOI field — regardless of whether other stages
  would later resolve one — does not trigger the abstract cascade.
- Semantic Scholar search results now carry the `abstract` field, which
  propagates through `_convert_search_metadata` into the final BibTeX
  output whenever the identification stage already resolved the entry
  through SS.
- `EnricherModule._get_semantic_scholar_abstract(doi)` helper for
  DOI-based Semantic Scholar abstract retrieval. Handles `404` / `429`
  gracefully by returning `None`.
- `_complete_fields` gained an `allow_abstract_fallback` kwarg
  (default `False`) that gates the new cascade. `_enrich_single_entry`
  passes `True` only when the raw entry contributed a DOI.
- Default `journal_article_full` template now lists `abstract` as an
  optional field, so the template declaration matches what the enricher
  emits. The older `journal_article_with_abstract` template is retained
  as a compatibility alias and will stay available for at least one
  release cycle.
- Regression test `test_enrich_single_entry_no_doi_in_raw_skips_abstract_fallback`
  pinning the "no-DOI-in raw ⇒ no Semantic-Scholar / PubMed network
  call" guarantee at the `_enrich_single_entry` layer, so a future
  refactor of the `raw_has_doi` gate cannot silently start leaking
  network calls for local-only inputs.

### Changed
- `_get_pubmed_abstract` now requires a DOI and no longer falls back to
  PubMed title search. The removed title-based path empirically returned
  the abstract of an unrelated paper (e.g., the Zhang 2020 automation Review DOI
  `10.1007/s10462-019-09792-7` pulled the abstract of a different RSI
  segmentation paper), which is strictly worse than returning `None` for
  downstream semantic cross-checks such as the `sci` skill.
- Abstract coverage on an internal 10-DOI cross-publisher spot-check
  (Nature, Science, PLOS, Cell, IEEE CVPR, Frontiers, arXiv, Springer,
  ACM, plus one deliberately invalid DOI) rose from 4/9 to 8/9. This
  number is a local indicator, **not** a release gate: reproducing it
  requires a live network and the probe scripts are no longer in the
  repository.

### Deprecated
- `_complete_fields(..., allow_pubmed_fallback=...)` is deprecated in
  favour of `allow_abstract_fallback`. The old name still works for one
  release cycle and emits `DeprecationWarning`. It was renamed because
  the flag actually gates the entire Semantic-Scholar + PubMed cascade,
  not PubMed alone.

### Removed
- `IdentifierModule._check_doi_content_consistency` and the
  `consistency_score` / `low_consistency` warning path. The fuzzy
  string-similarity score was empirically unable to detect subtle
  invalid references (scored 85/100 on author-only
  hallucinations against a real DOI) and was only surfaced as a
  `logger.warning` that downstream tools could not observe, producing
  false reassurance. Citation authenticity verification belongs at the
  abstract-vs-claim semantic layer in the consuming tool (e.g. the
  `sci` skill), not at the bibliographic-string layer here.

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
