

<div align="center">
  <p align="center">
    <img src="https://raw.githubusercontent.com/HzaCode/onecite/main/logo_.jpg" alt="OneCite Logo" width="160" />
  </p>

  <h1>OneCite</h1>
  <h3>Citation & Academic Reference Toolkit</h3>
</div>

<div align="center">

[![Downloads](https://img.shields.io/pepy/dt/onecite?style=flat-square&label=Downloads)](https://pepy.tech/project/onecite)
[![Awesome CLI Apps](https://img.shields.io/badge/🏆%20Featured-Awesome%20CLI%20Apps%20-FF6B35?style=flat-square)](https://github.com/agarrharr/awesome-cli-apps?tab=readme-ov-file#academia)

[![Tests](https://img.shields.io/github/actions/workflow/status/HzaCode/OneCite/tests.yml?style=flat-square&logo=github)](https://github.com/HzaCode/OneCite/actions)
[![codecov](https://img.shields.io/codecov/c/github/HzaCode/OneCite?style=flat-square&logo=codecov)](https://codecov.io/gh/HzaCode/OneCite)
[![PyPI](https://img.shields.io/pypi/v/onecite?style=flat-square&logo=pypi&color=blue)](https://pypi.org/project/onecite/)
[![Python](https://img.shields.io/badge/3.10+-blue?style=flat-square&logo=python)](https://www.python.org)
[![MIT](https://img.shields.io/badge/MIT-green?style=flat-square)](LICENSE)
[![Docs](https://img.shields.io/badge/Docs-Pages-blue?style=flat-square&logo=github)](https://hzacode.github.io/OneCite/)
[![Awesome LaTeX](https://img.shields.io/badge/Awesome-LaTeX-008B8B?style=flat-square&logo=awesome-lists&logoColor=white&labelColor=493267)](https://github.com/egeerardyn/awesome-LaTeX?tab=readme-ov-file#bibliography-tools)


</div>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-advanced-usage">📖 Advanced Usage</a> •
  <a href="#-roadmap">🗺️ Roadmap</a> •
  <a href="#-contributing">🤝 Contributing</a>
</p>

---

<p align="center">
  OneCite is a command-line tool and Python library for citation management. It resolves strong identifiers such as DOIs, PMIDs, arXiv IDs, ISBNs, GitHub URLs, and data DOIs into formatted bibliographic entries, while plain-text title searches are handled by the separate candidate-only suggest command.
</p>

---


 Researchers frequently accumulate reference lists in ad-hoc formats—DOIs copied from browser tabs, arXiv IDs from paper PDFs, PMIDs, ISBNs, software URLs, data DOIs, and BibTeX fragments from various sources. Cleaning these into consistent BibTeX output is tedious and error-prone. OneCite parses raw reference text and resolves strong identifiers against configured sources such as CrossRef, PubMed, arXiv, DataCite, GitHub, and Google Books. Plain-text title searches are exposed through `onecite suggest` so candidates can be reviewed without being mistaken for verified BibTeX. The result is a reproducible processing layer that reports unresolved entries and produces auditable BibTeX where metadata can be found.





---

## Features

| Feature                 | Description                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| **Candidate Suggestions**   | Search incomplete plain-text references with `onecite suggest` without resolving them to BibTeX.     |
| **Multiple Formats**        | Input `.txt`/`.bib` → Output **BibTeX**.                                                             |
| **4-stage Pipeline**        | A 4-stage process (clean → query → validate → format) to produce consistent output.                  |
| **Field Completion**        | Fill available fields returned by metadata sources, such as journal, volume, pages, authors, and abstract. |
| 🎓 **7+ Citation Types**    | Handles journal articles, conference papers, books, software, datasets, theses, and preprints.        |
| **Multi-Source Lookup**     | Uses source-specific routes for CrossRef, arXiv, PubMed, Semantic Scholar, Google Books, and others. |
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


## Quick Start

Install and try OneCite in a few steps.

### 1. Installation
```bash
# Recommended: Install from PyPI
pip install onecite
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
    interactive_callback=lambda candidates: -1
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
| `--output-format` | | Output format (currently only `bibtex` supported) | `bibtex` |
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
```

### `onecite suggest`

Search for candidate matches without producing BibTeX or returning a
validation `passed` status.

```bash
onecite suggest "Attention is all you need, Vaswani et al., NIPS 2017" --json
```

**Optional Google Scholar fallback.** `suggest` accepts `--google-scholar`
(requires the optional `scholarly` package: `pip install onecite[scholar]`).
It is consulted only as a best-effort fallback when CrossRef and Semantic
Scholar return nothing. Because it scrapes a service with no public API, it
is **off by default, may be rate-limited or blocked by a CAPTCHA, and is not
guaranteed to be reproducible** — it is exposed only on `suggest` (candidates
for human review), never on `process` (authoritative output).

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

**Examples:**
```bash
onecite benchmark
onecite benchmark --json
onecite benchmark --live --json
onecite benchmark --cases my_cases.json --min-success-rate 1.0 --json
```

The repository baseline record is stored at `benchmarks/leaderboard.json`, with
reproduction instructions in `benchmarks/README.md`.

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

## 🤝 Contributing

Contributions are always welcome! Please see [**CONTRIBUTING.md**](CONTRIBUTING.md) for development guidelines and instructions on how to submit a pull request.

## 📄 License

This project is licensed under the **MIT License**. See the [**LICENSE**](LICENSE) file for details.

<div align="center">

**OneCite**

<p>
  <a href="https://github.com/HzaCode/OneCite">Star on GitHub</a> •
  <a href="http://hezhiang.com/onecite">Web App</a> •
  <a href="https://github.com/HzaCode/OneCite/issues">🐛 Report an Issue</a> •
  <a href="https://github.com/HzaCode/OneCite/discussions">Discussions</a>
</p>

</div>
