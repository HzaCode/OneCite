

<div align="center">
  <p align="center">
    <img src="https://raw.githubusercontent.com/HzaCode/onecite/main/logo_.jpg" alt="OneCite Logo" width="160" />
  </p>

  <h1>OneCite</h1>
  <h3>Auditable citation normalization for research workflows</h3>
</div>

<div align="center">

[![Downloads](https://img.shields.io/pepy/dt/onecite?style=flat-square&label=Downloads)](https://pepy.tech/project/onecite)
[![Awesome CLI Apps](https://img.shields.io/badge/🏆%20Featured-Awesome%20CLI%20Apps%20-FF6B35?style=flat-square)](https://github.com/agarrharr/awesome-cli-apps?tab=readme-ov-file#academia)

[![Tests](https://img.shields.io/github/actions/workflow/status/HzaCode/OneCite/tests.yml?style=flat-square&logo=github)](https://github.com/HzaCode/OneCite/actions)
[![codecov](https://img.shields.io/codecov/c/github/HzaCode/OneCite?style=flat-square&logo=codecov)](https://codecov.io/gh/HzaCode/OneCite)
[![PyPI](https://img.shields.io/pypi/v/onecite?style=flat-square&logo=pypi&color=blue)](https://pypi.org/project/onecite/)
[![Python](https://img.shields.io/badge/3.10+-blue?style=flat-square&logo=python)](https://www.python.org)
[![MIT](https://img.shields.io/badge/MIT-green?style=flat-square)](LICENSE)
[![Docs](https://img.shields.io/badge/Docs-Pages-blue?style=flat-square&logo=github)](https://hezhiang.com/OneCite/)
[![Awesome LaTeX](https://img.shields.io/badge/Awesome-LaTeX-008B8B?style=flat-square&logo=awesome-lists&logoColor=white&labelColor=493267)](https://github.com/egeerardyn/awesome-LaTeX?tab=readme-ov-file#bibliography-tools)


</div>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#privacy-and-external-services">Privacy &amp; External Services</a> •
  <a href="#-advanced-usage">📖 Advanced Usage</a> •
  <a href="#-roadmap">🗺️ Roadmap</a> •
  <a href="#-contributing">🤝 Contributing</a>
</p>

---

<p align="center">
  OneCite is a command-line and Python toolkit that turns messy, mixed-format references — DOIs, PMIDs, arXiv IDs, ISBNs, URLs, and BibTeX fragments — into <strong>auditable</strong> BibTeX or CSL-JSON records. Strong identifiers follow documented metadata-service routes; ordinary ambiguous plain-text references are returned as candidates for review and are not auto-promoted by <code>process</code>.
</p>

---


AI-assisted writing, automated literature pipelines, and copy-paste research habits produce ever more reference objects in ever more formats — and ever more chances for wrong, fabricated, or mismatched bibliographic data. Reference *managers* (Zotero), *parsers* (AnyStyle, GROBID), *format converters* (Citation.js), and *identifier-to-BibTeX* helpers (doi2bib, Manubot) each solve one slice of the problem. OneCite targets the under-served step **before** references enter a manuscript, systematic review, or manager: an **auditable normalization layer** that routes strong identifiers (DOI, PMID, arXiv, ISBN, URL, data/software DOIs) to the applicable metadata services, completes available metadata, reports unresolved entries, and produces BibTeX or CSL-JSON.

OneCite is **not another reference manager**, and `process` does not auto-accept fuzzy title matches. Strong identifiers are resolved through documented source routes; explicitly labelled thesis/dissertation citations have a separate OpenAIRE/BASE route and can fall back to fields parsed from the input. Ordinary ambiguous text is returned as ranked candidates through `onecite suggest` for human review rather than silently emitted as source-resolved output. That `process`/`suggest` separation, together with machine-readable JSON/NDJSON, exit codes, and deterministic offline checks, makes OneCite a scriptable building block for agents, batch jobs, and reproducible reviews rather than a GUI library. Source resolution does not establish that a work is authentic, unretracted, or correctly described by upstream metadata.





---

## Features

| Feature                 | Description                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| **Candidate Suggestions**   | Search incomplete plain-text references with `onecite suggest` without promoting them to resolved bibliography output. |
| **Multiple Formats**        | Input `.txt`/`.bib` → Output **BibTeX** or **CSL-JSON**.                                             |
| **4-stage Pipeline**        | A 4-stage process (parse → identify → enrich → format) with explicit unresolved entries.             |
| **Field Completion**        | Fill available fields returned by metadata sources, such as journal, volume, pages, authors, and abstract. |
| 🎓 **7+ Citation Types**    | Handles journal articles, conference papers, books, software, datasets, theses, and preprints.        |
| **Input-Routed Lookup**     | Uses source-specific routes for Crossref, arXiv, PubMed, Semantic Scholar, Google Books, and others. Not every source is queried for every input. |
| **Many Identifier Types**   | Resolves DOI, PMID, arXiv ID, ISBN, GitHub URL, Zenodo DOI, and DataCite DOI inputs.                 |
| **Custom Templates**        | YAML-based presets that provide a fallback BibTeX entry type when auto-detection is inconclusive.    |


## 🌐 Data Sources

<div align="center">

[![CrossRef](https://img.shields.io/badge/CrossRef-B31B1B?style=for-the-badge&logo=crossref&logoColor=white)](https://www.crossref.org/)
[![Semantic Scholar](https://img.shields.io/badge/Semantic-1857B6?style=for-the-badge&logo=semanticscholar&logoColor=white)](https://www.semanticscholar.org/)
[![PubMed](https://img.shields.io/badge/PubMed-326599?style=for-the-badge&logo=pubmed&logoColor=white)](https://pubmed.ncbi.nlm.nih.gov/)
[![arXiv](https://img.shields.io/badge/𝒳_arXiv-B31B1B?style=for-the-badge)](https://arxiv.org/)
[![DataCite](https://img.shields.io/badge/DataCite-00B4A0?style=for-the-badge&logo=datacite&logoColor=white)](https://datacite.org/)
[![Zenodo](https://img.shields.io/badge/Zenodo-0A0E4A?style=for-the-badge&logo=zenodo&logoColor=white)](https://zenodo.org/)
[![Google Books](https://img.shields.io/badge/Google-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://books.google.com/)
</div>

### Privacy and external services

Normal `process` and `suggest` runs can make input-dependent outbound requests.
For example, DOI resolution sends the DOI to Crossref (and sometimes a
fallback registry); `suggest` sends citation queries to Crossref, Semantic
Scholar, and arXiv; arbitrary URL input is fetched from the supplied host; and
thesis queries can be sent to OpenAIRE and BASE. Google Scholar is an optional,
scraping-based `suggest` fallback that is off by default and may be blocked or
challenged by a CAPTCHA.

OneCite does not provide a privacy-compliance guarantee or a persistent cache
of ordinary live responses. Providers, proxies, output files, and logs may
retain data. Review and redact confidential input before use. See
[Privacy and external services](docs/external_services.rst) for the exact
`process`/`suggest` routes, transmitted fields, source-health limits, and the
offline benchmark/doctor boundary.


## Quick Start

Install and try OneCite in a few steps.

### 1. Installation

The current public PyPI release is `0.1.1`. This working tree documents the
unreleased `0.2.0` candidate, so install from the checkout when verifying
candidate-only behavior:

```bash
# Current stable public release
pip install onecite

# Unreleased 0.2.0 candidate, from the repository checkout
python -m pip install -e .
```

### 2. Create an Input File
Create a file named `references.txt` with your mixed-format references:
```text
# references.txt
# Add blank lines between entries to avoid misidentification

10.1038/nature14539

arXiv:1706.03762

ISBN:9780262035613

https://github.com/tensorflow/tensorflow

10.5281/zenodo.3233118

arXiv:2103.00020

Smith, J. (2020). Neural Architecture Search. PhD Thesis. Stanford University.
```

### 3. Run OneCite
Execute the command to process your file and generate a clean `.bib` output.
```bash
onecite process references.txt -o results.bib --quiet
```

### 4. View Output
Your `results.bib` file now contains entries of different types.

<details>
<summary><strong>View Complete Output (results.bib)</strong></summary>

```bibtex
@article{LeCun2015Deep,
  doi = "10.1038/nature14539",
  title = "Deep learning",
  author = "LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey",
  journal = "Nature",
  year = 2015,
  volume = 521,
  number = 7553,
  pages = "436-444",
  publisher = "Springer Science and Business Media LLC",
  url = "https://doi.org/10.1038/nature14539",
  type = "journal-article",
  abstract = "Deep learning allows computational models that are composed of multiple processing layers to learn representations of data with multiple levels of abstraction...",
}
@inproceedings{Vaswani2017Attention,
  arxiv = "1706.03762",
  title = "Attention Is All You Need",
  author = "Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N. and Kaiser, Lukasz and Polosukhin, Illia",
  year = 2017,
  booktitle = "Advances in Neural Information Processing Systems (NeurIPS)",
  url = "https://arxiv.org/abs/1706.03762",
}
# ... and 5 more entries ...
```

</details>

## 📖 Advanced Usage

<details>
<summary><strong>Direct String and Stdin Input</strong></summary>

```bash
onecite process "10.1038/nature14539"
onecite suggest "Attention is all you need, Vaswani et al., NIPS 2017"
echo "10.1038/nature14539" | onecite process -
```
</details>

<details>
<summary><strong>🐍 Use as a Python Library</strong></summary>

Use OneCite directly in your Python scripts.

```python
from onecite import process_references

result = process_references(
    input_content="10.1038/nature14539",
    input_type="txt",
    template_name="journal_article_full",
    output_format="bibtex",
)

print('\n\n'.join(result['results']))
```
</details>

<details>
<summary><strong>💻 CLI Commands & Options</strong></summary>

OneCite provides a command-line interface with the following commands and options:

### `onecite process`

The main command for processing references through the OneCite pipeline.

**Usage:**
```bash
onecite process <input_file> [OPTIONS]
```

**Arguments:**
- `input_file` - Input file path, `-` for stdin, or a strong identifier/reference string

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input-type` | | Input format: `txt` or `bib` | `txt` |
| `--template` | | Fallback BibTeX entry-type preset when auto-detection is inconclusive | `journal_article_full` |
| `--output-format` | | Output format: `bibtex` or `csl-json` for downstream tools that consume CSL-JSON | `bibtex` |
| `--output` | `-o` | Output file path (default: stdout) | - |
| `--quiet` | `-q` | Suppress verbose logging output | `False` |
| `--json` | | Print a stable JSON envelope instead of BibTeX text | `False` |
| `--ndjson` | | Print newline-delimited JSON events for streaming automation workflows | `False` |
| `--fail-on-unresolved` | | Return exit code `2` when any entry cannot be resolved | `False` |

**Examples:**
```bash
# Process a text file
onecite process references.txt -o results.bib

# Process a BibTeX file with auto-detection
onecite process references.bib

# Use stdin
echo "10.1038/nature14539" | onecite process -

# Process a direct string (DOI)
onecite process "10.1038/nature14539"

# Process with custom template
onecite process references.txt --template conference_paper

# Quiet mode for scripts
onecite process references.txt -o results.bib --quiet

# Automation-friendly JSON with unresolved-entry exit-code handling
onecite process references.txt --json --fail-on-unresolved

# Streaming NDJSON for automation
onecite process references.txt --ndjson

# CSL-JSON item output (a development fixture verifies Pandoc 3.10 consumption)
onecite process references.txt --output-format csl-json -o references.json
```

The development evidence verifies Pandoc 3.10 consumption of representative
emitted items. Quarto, standalone citeproc, and reference-manager import
workflows are not separately validated in this release.

**Report fields.** Beyond `results` and `failed_entries`, the processing
report carries two audit signals:

- `warnings` — non-blocking review warnings on *resolved* entries. Most
  importantly `text_metadata_mismatch`: the input text around a resolved DOI
  appears to describe a **different** work (the classic hallucinated
  title+DOI pairing). The DOI remains the resolved identifier and the entry resolves,
  but it is flagged for review instead of silently emitted as clean output.
- `duplicates` — the same work appeared more than once in the batch (bare
  DOI, PMID, formatted citation). It is emitted once; repeats are reported
  with the emitted entry's cite key.

Failed entries carry the original input excerpt (`raw_text`) and a `reason`
code — `doi_not_found` (no registry record was returned after the implemented
fallback), `no_strong_identifier` (ambiguous text; use `onecite suggest`),
`source_error` (a source/identity failure surfaced on that route), and more.
These codes make important cases distinguishable, but they are not a complete
provider trace: some PMID, ISBN, and DataCite request errors currently collapse
into the same unresolved reason as a lookup miss.

### `onecite suggest`

Search for candidate matches without producing BibTeX or returning a
validation `passed` status.

```bash
onecite suggest "Attention is all you need, Vaswani et al., NIPS 2017" --json
```

**Candidates are for review, not source-resolved citations.** Each suggestion
discloses the health of the consulted scholarly indexes in a `sources`
list. If a source was rate-limited or errored, the suggestion status becomes
`candidates_found_incomplete` / `no_candidates_incomplete` — the correct
match may be missing from the list entirely, and the candidate list must
not be treated as exhaustive. Candidates whose year contradicts the year
cited in the query are penalized and flagged with `year_conflict`. To turn
a reviewed candidate into source-resolved BibTeX, resolve its DOI through
`onecite process "<doi>"`.

**Optional Google Scholar fallback.** `suggest` accepts `--google-scholar`
(requires the optional `scholarly` package: `pip install onecite[scholar]`).
It is consulted only as a best-effort fallback when CrossRef and Semantic
Scholar return nothing. Because it scrapes a service with no public API, it
is **off by default, may be rate-limited or blocked by a CAPTCHA, and is not
guaranteed to be reproducible** — it is exposed only on `suggest` (candidates
for human review), never on `process`.

```bash
pip install onecite[scholar]
onecite suggest "some obscure title" --google-scholar
```

### `onecite --version`

Display the installed OneCite version.

**Usage:**
```bash
onecite --version
```

### `onecite version`

Alternative command to display version information.

**Usage:**
```bash
onecite version
```

### `onecite templates`

List the bundled fallback BibTeX templates and the fields they request.

**Usage:**
```bash
onecite templates
onecite templates --json
```

### `onecite benchmark`

Run a small deterministic regression suite for covered DOI lookup, arXiv
lookup, PMID/PubMed lookup, GitHub software URLs, Zenodo/DataCite dataset
DOIs, and mixed valid/invalid batches. The command is designed for CI and
automation workflows that need a machine-readable pass/fail check; it is not
a comprehensive citation-accuracy benchmark.

**Usage:**
```bash
onecite benchmark [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--cases` | Path to a custom benchmark suite JSON file | bundled golden cases |
| `--min-success-rate` | Minimum covered-case pass rate required for exit code `0` | `1.0` |
| `--json` | Print the benchmark report as JSON | `False` |
| `--live` | Use live external APIs instead of bundled offline fixtures | `False` |
| `--anti-hallucination` | Run the labelled non-fabrication evaluation instead of the golden cases | `False` |

**Examples:**
```bash
onecite benchmark
onecite benchmark --json
onecite benchmark --live --json
onecite benchmark --cases my_cases.json --min-success-rate 1.0 --json
onecite benchmark --anti-hallucination
onecite benchmark --anti-hallucination --json
```

The repository baseline record is stored at `benchmarks/leaderboard.json`, with
reproduction instructions in `benchmarks/README.md`.

#### Anti-hallucination evaluation

`onecite benchmark --anti-hallucination` runs a labelled, fully-offline
evaluation of OneCite's core safety property. It resolves real strong
identifiers (class **A**) into source-resolved BibTeX, leaves ambiguous
plain-text references (class **B**) and fabricated, non-existent DOIs (class
**C** — the kind a language model may hallucinate) **unresolved** rather than
emitting a wrong citation, and flags mismatched pairings (class **D** — a real
DOI attached to a *different* paper's title, the most common hallucinated-citation
shape) with a `text_metadata_mismatch` warning instead of silently emitting them
as clean source-resolved output. It reports three metrics:

- **resolution rate** — fraction of class-A inputs correctly resolved;
- **non-fabrication rate** — fraction of class-B/C inputs correctly left
  *unresolved* (not fabricated). `100%` means OneCite invented no citations;
- **mismatch detection rate** — fraction of class-D inputs resolved *with*
  the mismatch warning attached.

A pipeline crash is recorded as `error` and never counts as correct for any
metric — a clean rejection and a broken pipeline are different outcomes.

The dataset lives at `src/onecite/benchmarks/anti_hallucination_cases.json`, and the
evaluation is also available from Python via
`onecite.run_anti_hallucination_eval()`.

### `onecite doctor`

Check the local installation health for automation and CI. The doctor
command checks package importability, bundled templates, packaged benchmark
resources, the repository-contained OneCite Skill, and the offline benchmark
regression check.

**Usage:**
```bash
onecite doctor
onecite doctor --json
```

The JSON output is a stable envelope with `schema_version`, `tool`,
`command`, `status`, `environment`, `summary`, and `checks` fields.

### OneCite Skill for Automated Workflows

The repository includes a local skill package at `skills/onecite/SKILL.md`.
It gives automation and contributor workflows a repeatable procedure for
reference cleanup, benchmark and doctor checks, and explicit
reporting of unresolved entries.
The skill is repository-contained and does not install itself into any local
tool memory.

### Input Type Auto-Detection

When `--input-type` is not specified, OneCite automatically detects the input type:
- Files ending with `.bib` are treated as BibTeX format
- All other files and strings are treated as plain text

### Available Templates

OneCite supports several template presets for different entry types:
- `journal_article_full` - Full journal article entry (default)
- `conference_paper` - Conference proceedings paper
- `book` - Book entry
- `thesis` - Thesis/dissertation entry
- `dataset` - Dataset entry
- `software` - Software/code entry

### Exit Codes

- `0` - Success
- `1` - Error occurred (invalid input, processing failure, etc.)
- `2` - One or more entries were unresolved when `--fail-on-unresolved` was used

For `onecite benchmark` and `onecite doctor`, exit code `0` means the
configured checks passed and exit code `1` means at least one check failed.

</details>

## 🗺️ Roadmap

- [x] **OneCite Skill** — Repository-contained operating guide for local citation-cleanup workflows
- [x] **Benchmarking** — Small deterministic regression suite, configurable pass-rate gate, and baseline record
- [x] **Enhanced CLI** — Automation-friendly JSON, NDJSON, summaries, and exit codes for reference processing
- [x] **Anti-hallucination evaluation** — Labelled offline eval of the non-fabrication property (resolution, non-fabrication, and mismatch detection rates), gated in CI
- [x] **Audit-grade reports** — Text/DOI mismatch warnings, failure reason codes with original input, DOI-level deduplication, and suggest source-health disclosure
- [x] **CSL-JSON output** — `--output-format csl-json` emits CSL-JSON items for downstream tools that consume the format; a development fixture verifies Pandoc 3.10 consumption, while Quarto, standalone citeproc, and reference-manager imports are not separately validated
- [x] **Expanded suggest sources** — Direct arXiv candidate search covers the CS venues that CrossRef does not index
- [ ] **Concurrent batch resolution** — Parallel source lookups for large reference lists (currently sequential; latency depends on the selected routes and external services)
- [ ] **Larger anti-hallucination dataset** — More labelled cases per class and a published live-mode baseline

## 🤝 Contributing

Contributions are always welcome! Please see [**CONTRIBUTING.md**](CONTRIBUTING.md) for development guidelines and instructions on how to submit a pull request.

## 📄 License

This project is licensed under the **MIT License**. See the [**LICENSE**](LICENSE) file for details.

<div align="center">

**OneCite**

<p>
  <a href="https://github.com/HzaCode/OneCite">Star on GitHub</a> •
  <a href="https://hezhiang.com/OneCite/">Documentation</a> •
  <a href="https://github.com/HzaCode/OneCite/issues">🐛 Report an Issue</a> •
  <a href="https://github.com/HzaCode/OneCite/discussions">Discussions</a>
</p>

</div>
