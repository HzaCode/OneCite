# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Enhanced CLI modes for automated workflows: `onecite process --json`,
  `onecite process --ndjson`, and `--fail-on-unresolved` exit code `2`
  for unresolved-entry handling in scripts.
- `onecite benchmark` CLI command with bundled deterministic golden
  cases, JSON output, and a configurable success-rate regression gate for
  covered cases, plus a repository baseline record
  at `benchmarks/leaderboard.json`.
- Expanded the bundled benchmark suite to cover PMID/PubMed lookup,
  GitHub software URLs, Zenodo/DataCite dataset DOIs, and more explicit
  benchmark-suite schema validation.
- `onecite doctor` CLI command with stable JSON output for package,
  template, benchmark-resource, skill-package, and offline benchmark
  health checks.
- CLI contract documentation for JSON/NDJSON process reports, benchmark
  reports, doctor reports, stdout/stderr behavior, and exit codes.
- Repository-contained OneCite Skill package at `skills/onecite/SKILL.md`
  with metadata-lookup and validation-check operating instructions.
- `onecite templates` CLI command for listing bundled fallback BibTeX
  templates, including machine-readable `--json` output for tools that
  need to inspect available presets.
- Contract-level regression tests for process JSON/NDJSON, benchmark
  JSON, doctor JSON, and template JSON envelopes used by automation and CI.
- `build>=1.0` is now included in the development extra so the documented
  wheel build check works after `pip install -e ".[dev]"`.
- `onecite benchmark --anti-hallucination`: a labelled, fully-offline evaluation
  of OneCite's non-fabrication property (resolution rate on real identifiers;
  non-fabrication rate on ambiguous text and fabricated DOIs; mismatch
  detection rate on real DOIs paired with a different paper's title), also
  exposed as `onecite.run_anti_hallucination_eval()`. Pipeline crashes are
  recorded as `error` and never count as correct.
- Text/DOI consistency warning: when the descriptive text around a resolved
  DOI clearly describes a different work (the classic hallucinated title+DOI
  pairing), `process` still resolves from the authoritative DOI but attaches
  a non-blocking `text_metadata_mismatch` warning, surfaced in the report,
  the JSON/NDJSON envelopes, and the CLI summary. Consistency requires
  *positive* overlap — the text must contain most of the title's words or
  most of the authors' family names; character-level fuzz alone is not
  accepted as evidence (it has a blind spot for short titles like "Deep
  learning"). A year cited in the text that contradicts the resolved
  metadata by more than five years raises the required overlap further.
- Auditable failure reports: failed entries now carry the original input
  text (`raw_text`) and a `reason` code (`doi_not_found`, `source_error`,
  `pmid_unresolved`, `isbn_unresolved`, `no_strong_identifier`, and more) so
  a safely rejected identifier, an ambiguous reference, and an unavailable
  source can be told apart; identification-stage failures are no longer
  mislabelled as `enrichment_failed`.
- DOI-level deduplication: when the same work appears several times in a
  batch under different spellings (bare DOI, PMID, formatted citation), it
  is emitted once and the repeats are reported as `duplicates` (with the
  emitted entry's cite key) instead of re-emitted under suffixed keys.
- `onecite benchmark --anti-hallucination` now refuses `--cases` and
  `--min-success-rate` instead of silently ignoring them.

- `onecite suggest` now searches arXiv directly alongside CrossRef and
  Semantic Scholar. arXiv covers the CS/ML venues that CrossRef does not
  index (e.g. NeurIPS/ICML), which previously made famous conference papers
  unfindable when Semantic Scholar was rate-limited; the title-field query
  is derived from the segment before the first comma of the citation.
- CSL-JSON output: `onecite process --output-format csl-json` emits a valid
  CSL-JSON array (plain Unicode, structured author names, mapped item types)
  for downstream tools that consume CSL-JSON; a development fixture verifies
  Pandoc 3.10 consumption of representative emitted items, while Quarto,
  standalone citeproc, and reference-manager import workflows are not
  separately validated in this release;
  `process_references(output_format="csl-json")` returns one CSL item per
  result. Deduplication, warnings, and failure reporting apply unchanged.
- Honest suggestion scoring: when the query explicitly cites a year, a
  candidate contradicting it by more than five years is penalized and
  flagged (`year_conflict` in `score_breakdown`) — same-title later works
  (commentaries, book chapters, reprints) no longer outrank on title
  similarity alone. Year and venue scores are now gated by title similarity,
  so unrelated works sharing only a year or a phrase fragment no longer
  climb the ranking.
- `onecite suggest` now discloses source health: each suggestion carries a
  `sources` list with the status of the always-consulted scholarly indexes
  (CrossRef, Semantic Scholar) and per-source candidate counts. When a
  source is rate-limited or errors, the suggestion status becomes
  `candidates_found_incomplete`/`no_candidates_incomplete` and the CLI
  prints a notice — an incomplete candidate list is no longer presented as
  exhaustive. Semantic Scholar rate limits are retried once with backoff.

### Changed
- Moved the importable package from the repository root to
  `src/onecite`, adopting the standard `src/` repository layout while
  retaining the public `onecite` module and CLI names.
- Installed data files are now limited to artifacts with an actual consumer
  (the OneCite Skill file and the benchmark baseline, both located by
  `onecite doctor`). Documentation is no longer installed into
  `sys.prefix/share` — it ships in the source distribution and lives on the
  documentation site; the wheel drops from 56 to 33 files.
- Default pytest runs now exclude live external-API checks;
  live checks are explicitly marked with `pytest.mark.live` so the
  default suite is deterministic and offline.
- The bundled benchmark now uses the same non-interactive ambiguous
  candidate policy as `onecite process`: skip candidates unless the
  user explicitly opts into an interactive flow.
- The OneCite Skill now documents local validation checks, benchmark
  evidence, doctor checks, and release-readiness evidence reporting.
- Bundled YAML templates are now declared as the explicit
  `onecite.templates` package so wheel builds do not emit the implicit
  package warning for template assets.
- Removed the unused `setuptools_scm` build requirement; OneCite uses a
  static project version, so wheel builds no longer warn about missing
  SCM configuration.
- Modernized package license metadata to the SPDX `MIT` form with
  explicit license-file packaging, using a setuptools version that
  supports the current pyproject license contract.
- Reformatted the package and tests with Black, removed stale imports and
  unused locals, aligned flake8 with Black for long lines, and made CI run
  the same `flake8 src/onecite tests` check documented in the OneCite
  Skill release checklist.
- Aligned the OneCite Skill with the repository's actual Roadmap source
  in the `README.md` Roadmap section and the `flake8 src/onecite tests`
  validation check.

### Removed
- `onecite process` no longer accepts `--google-scholar`, and
  `process_references()` no longer accepts the `use_google_scholar`
  parameter. Google Scholar was never consulted from the authoritative
  `process` path, so the flag and parameter were no-ops there. Google
  Scholar remains available as an opt-in, best-effort fallback on
  `onecite suggest --google-scholar` /
  `suggest_references(use_google_scholar=True)`.
- Removed the non-functional `--interactive` flag from `onecite process` and the
  dead interactive/fuzzy-adoption code (`_fuzzy_search`,
  `_resolve_doi_via_crossref_title`). Plain-text disambiguation is handled by
  `onecite suggest`; `process` resolves only strong identifiers. The
  `interactive_callback` parameter remains as a no-op compatibility shim.
- Removed best-effort metadata scraping of arbitrary HTML/PDF pages
  (`_extract_metadata_from_url` and helpers, which also relied on an undeclared
  PyPDF2 dependency) and the body-text DOI fallback in `_extract_doi_from_url`.
  URL resolution now trusts only a publisher-declared `citation_doi` /
  schema.org identifier (verified downstream), consistent with the
  strong-identifier-only contract of `process`.

### Fixed
- The bundled DataCite and Zenodo fixtures used a dead Dryad DOI and a
  fabricated Zenodo title, so `benchmark --live` failed on real APIs even
  though the offline run passed. Both now mirror real, long-lived records
  (`10.5061/dryad.8515`; Zenodo `3233118` = nibabel 2.4.1), and the golden
  + anti-hallucination suites both passed live in their then-current forms on
  2026-07-03. Those historical fixtures are regression smoke checks, not a
  general effectiveness estimate; the later 11-case development smoke suite
  is tracked separately. Live baseline records were added to
  `benchmarks/`.
- The test-suite mock responses are now derived from the bundled offline
  fixtures instead of hand-maintaining a second copy of the same DOIs'
  metadata; the two copies had already drifted (`URL` and citation counts
  missing on one side, `ISSN` on the other) and consistency tests now pin
  the derivation.
- The documentation changelog (`docs/changelog.rst`) had silently drifted
  from `CHANGELOG.md` (16 Unreleased entries missing) and the Unreleased
  section contained a duplicated `### Fixed` heading; both are fixed and
  the docs page now states that `CHANGELOG.md` is canonical.
- `process_references` no longer requires the `interactive_callback`
  argument. The parameter was never invoked by the pipeline — `process` is
  strictly non-interactive — yet the signature forced every caller to pass a
  dummy lambda and the docs described selection behavior that did not exist.
  It is now optional, documented as never invoked, and retained only for
  backward compatibility; the Python API examples were corrected accordingly.
- Google Books lookups now retry with backoff on HTTP 429/5xx instead of
  failing the ISBN entry on the first rate-limit response.
- `onecite process --template` now rejects unknown template names with the
  list of valid presets instead of silently falling back to the default
  template; the Python-level `TemplateLoader` fallback logs a warning.
- Explicitly labelled PMIDs embedded in citation text (e.g.
  `"Author (2015). Deep learning. PMID:26017442"`) now resolve, matching
  the long-standing behavior for DOIs embedded in text. Unlabelled numbers
  inside prose remain ambiguous and are not extracted.
- The arXiv suggestion source now queries the `https` endpoint directly
  (the `http` URL 301-redirected on every call), retries transient
  429/5xx responses with a short backoff, and truthfully discloses a
  still-throttled source as `rate_limited` instead of `error`.
- The test suite now fails loudly on any unmocked network call from a
  non-`live` test (autouse guard in `conftest.py`). This exposed unit
  tests that had been silently hitting live APIs whenever a suggestion
  source was missing from their mock list, and cut the full-suite runtime
  from ~43s to ~6s.
- Eliminated a duplicate CrossRef API call per DOI entry: the work object
  fetched during DOI verification is now reused for enrichment instead of
  requesting the same DOI from CrossRef a second time — halving CrossRef
  load and saving up to a second of latency per entry in live runs.
- Cite-key generation is now LaTeX-safe and crash-free: accented author
  names are ASCII-folded (Müller → Muller), characters with no ASCII form
  (CJK) are dropped instead of emitted into `\cite{...}` keys, and an
  integer `year` (as DataCite's `publicationYear` delivers) no longer
  raises `TypeError`.
- CSL-JSON values now strip *all* LaTeX case-protection braces instead of
  mangling inner ones (`{ResNet}: ...` previously became the unbalanced
  `ResNet}: ...`), and BibTeX `--` page ranges are normalized to plain
  `-` as CSL expects.
- An unwritable `--output` path no longer discards computed results or
  misattributes the IO failure as a processing failure: `process` and
  `suggest` now emit the computed output to stdout with a clear error on
  stderr and exit `1`, so expensive live-API work is never lost.
- `onecite doctor` now verifies the bundled anti-hallucination dataset as
  part of the `benchmark_resources` check, so a broken install cannot
  report healthy benchmark resources while the core safety-evaluation
  asset is missing.
- Removed the undocumented `sugget` CLI alias (a development-time typo
  for `suggest` that leaked into the subcommand list).
- `onecite suggest --input-type bib` no longer sends a Python dict repr to
  the scholarly indexes when a BibTeX entry carries a DOI: the search query
  is now always built from the structured title/author/year fields.
- OneCite's own BibTeX output now survives re-processing through
  `--input-type bib` byte-identically for all entry kinds, locked in by
  round-trip tests. Two defects were closed: bibtexparser silently dropped
  non-standard entry types, so OneCite could not re-parse its own
  `@software` entries; and a non-empty BibTeX file that parsed to zero
  entries produced an empty "success" (exit 0, empty output) instead of a
  loud `ParseError`.
- The Sphinx documentation now builds with zero warnings (fixed broken
  section underlines in the changelog and FAQ, removed the nonexistent
  `_static` path and the deprecated `display_version` theme option), and
  the docs CI build runs with `-W` so new warnings fail the build.
- The mypy configuration declared in `pyproject.toml` is now actually
  enforced: all 70 outstanding type errors were fixed and `mypy src/onecite`
  runs in CI. This closed several latent crash paths — an `HTTPError`
  handler that dereferenced a possibly-absent `response` object,
  `json.loads(None)` on empty structured-data script tags in publisher
  pages, a possibly-unset Google Books retry response, and unguarded
  `.get()` calls on possibly-`None` metadata dicts in the enricher.
- Corrected the benchmark Nature DQN DOI fixture from
  `10.1038/nature14539` to `10.1038/nature14236`, and added regression
  coverage to catch future DOI-title-author mismatches in bundled
  golden cases.
- Added benchmark expectation checks for expected failed entries so
  mixed valid/invalid cases must exercise unresolved-entry reporting.
- Added the documented `onecite version` subcommand alongside
  `onecite --version`.
- Fixed LaTeX formatting for curly single and double quotes.
- Blocked live CrossRef/Semantic Scholar calls in fuzzy-search unit
  tests unless a test opts into a mocked source explicitly.
- Kept machine-readable JSON/NDJSON stdout clean when `--output` is
  used by routing the saved-file status message to stderr.
- Included the OneCite Skill and benchmark baseline files in built
  distribution artifacts.
- Added benchmark and doctor checks to the GitHub Actions test
  workflow.
- Hardened benchmark suite validation for malformed expectation
  contracts and impossible minimum-count combinations.
- Added regression coverage showing the default offline benchmark check
  overrides live HTTP calls with bundled source fixtures.
- Fixed the benchmark success-rate gate to compare the unrounded
  `passed / total_cases` ratio instead of the rounded display value.
- Added machine-readable `onecite process --json` and `--ndjson` failure
  envelopes for hard processing errors before per-entry results exist.
- Clarified that `onecite benchmark --json` is the deterministic offline
  health check, while `onecite process ...` may contact upstream APIs
  unless fixtures or mocks are explicitly configured.
- DOI-backed BibTeX input now keeps the canonical CrossRef/DataCite field
  values instead of letting the original entry override them; original
  fields still fill gaps the API leaves empty, and the existing citation
  key is still preserved.
- A CrossRef 404 now always falls back to DataCite instead of only doing so
  for a short hardcoded prefix list, so dataset/software/thesis DOIs
  registered under other DataCite prefixes resolve.
- `suggest` no longer routes queries containing words such as "synthesis",
  "hypothesis", or "parenthesis" to the thesis search (whole-word match for
  "thesis"/"dissertation").
- GitHub clone URLs ending in `.git` now resolve to the correct repository.
- Plain-text entry ids stay contiguous when entries are separated by more
  than one blank line, and a dead PLOS article-id branch was removed from
  the text parser.
- `suggest` candidate ranking now applies the tie-break (exact title, venue,
  DOI, source tier) within the cluster of candidates scoring within 5 points of
  the top, instead of letting a fractionally higher raw score always win.
- BibTeX output now LaTeX-escapes the `abstract` and `editor` fields (not just
  author/title/journal/...), so Unicode in those fields no longer leaks raw
  into the `.bib` output.

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
  the abstract of an unrelated paper (e.g., a Zhang 2020 example DOI
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
  `consistency_score` / `low_consistency` warning path. A fuzzy
  string-similarity score on bibliographic fields is not a reliable
  signal for detecting fabricated references, and it was only emitted
  as a `logger.warning` that downstream tools could not act on.
  Citation-authenticity verification belongs at the abstract-vs-claim
  semantic layer in the consuming tool, not at the bibliographic-string
  layer here.

## [0.1.0] - 2026-04-17

First formal PyPI release since `0.0.12`.

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
  plus a `_utils.py` for shared helpers.  Public imports
  (`from onecite.pipeline import IdentifierModule`) and mocking targets
  (`patch("onecite.pipeline.requests.get", ...)`) continue to work
  unchanged because `__init__.py` re-exports every public symbol and
  keeps `requests` at the package level.
- Unify CrossRef request and parsing methods; all CrossRef calls
  now go through a single helper with a proper `User-Agent` header and
  `mailto` query-string parameter.
- Rewrite fuzzy-search scoring as a weighted title / author / year /
  venue model with three confidence tiers (auto-adopt / interactive /
  cautious) and a unified low-confidence threshold.
- Simplify identifier routing; CrossRef and Semantic Scholar are always
  consulted for text queries, with signal-based additional queries to
  PubMed / Google Books / external providerRE / BASE.
- Use `bibtexparser.dumps()` for BibTeX rendering.
- Expose `use_google_scholar` as a real CLI flag and API parameter
  instead of a hard-coded `False`.
- Clarify that templates define metadata-field requirements and a
  fallback BibTeX entry type, not output formatting.
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
  or citeproc-py.
- Hard-coded "well-known paper" shortcut that masked failures on the
  main example input.
- MCP integration page and all related references
- `.readthedocs.yml` (docs now hosted on GitHub Pages)
- `docs/_build/` build artifacts from repository

### Fixed
- README / `docs/index.rst` / `docs/faq.rst` no longer advertise
  OpenAlex or dblp as data sources — they were never wired into the
  code.
- README quick-start example now shows `booktitle` (NeurIPS) instead
  of `journal = "arXiv preprint"` for the `@inproceedings` sample.
- `docs/api/pipeline.rst` rewritten to match the actual module
  structure; removed references to classes and methods that never
  existed (`Validator` / `Identifier` / `Completer` / `Formatter`,
  `set_source_priority`, `set_timeout`, `add_template_path`).
- `docs/output_formats.rst`, `docs/faq.rst`, `docs/quick_start.rst`,
  `docs/python_api.rst`, `docs/templates.rst`, `docs/index.rst` and
  docstrings in `core.py` / `formatter.py` no longer advertise APA /
  MLA output.
- Crossref author names parsed as `given family` instead of mangled
  concatenations.
- Semantic Scholar HTTP 429 responses return an empty candidate list
  cleanly instead of bubbling up.
- Previously-unused exception classes (`ParseError`, `ValidationError`,
  `FormatError`) are now actually raised in the right places.
- `CONTRIBUTING.md` no longer tells developers to use a `requirements.txt`
  that does not exist; the documented install is `pip install -e .[dev]`.
- `black` formatting is enforced via `pyproject.toml` `[tool.black]`
  plus a pre-commit hook.
- URL-bearing entries are no longer queried twice.
- Fallback paths mark entries as `identification_failed` rather than
  fabricating plausible-looking but invented metadata.
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
