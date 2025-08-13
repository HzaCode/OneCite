
<!-- Logo -->
<p align="center">
  <img src="logo_.jpg" alt="OneCite Logo" width="140" />
</p>

<h1 align="center">OneCite</h1>
<p align="center"><em>Universal Citation Management & Academic Reference Toolkit</em></p>

<p align="center">
  <a href="https://pypi.org/project/onecite/">
    <img src="https://img.shields.io/pypi/v/onecite.svg" alt="PyPI version">
  </a>
  <a href="https://www.python.org">
    <img src="https://img.shields.io/badge/Python-3.7+-blue.svg" alt="Python">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Status-Alpha-orange.svg" alt="Status">
</p>

<p align="center"><em>Go beyond traditional managers: Transform messy references into perfect citations.</em></p>

<p align="center">
  <a href="#-features">✨ Features</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-advanced-usage">💡 Advanced Usage</a> •
  <a href="#-configuration">⚙️ Configuration</a> •
  <a href="#-template-system">🎨 Template System</a> •
  <a href="#-contributing">🤝 Contributing</a> •
  <a href="#-license">📄 License</a>
</p>

---

## ✨ Features

- 🔍 **Smart Recognition** — Fuzzy matching with CrossRef & Google Scholar APIs  
- 📚 **Multi-format Support** — TXT, BibTeX input → BibTeX, APA, MLA output  
- 🎯 **High Accuracy** — 4-stage refinement pipeline ensures quality  
- 🤖 **Auto-completion** — Intelligently fills missing bibliographic data  
- 🎛️ **Interactive Mode** — User choice for ambiguous matches  
- ⚙️ **Template System** — Flexible output field configuration  
- 🎓 **Conference Paper Support** — Recognizes papers from NIPS/NeurIPS, CVPR, ICML, etc.  
- 📄 **arXiv Integration** — Automatically fetches metadata for arXiv papers

---

## 🚀 Quick Start

### Installation

#### Option 1: Install from PyPI (Recommended)
```cmd
pip install onecite
````

#### Option 2: Install from Source

```cmd
git clone https://github.com/HzaCode/onecite.git
cd onecite
pip install -r requirements.txt
pip install -e .
```

### Basic Usage

**Input** (`references.txt`):

```text
10.1038/nature14539

Attention is all you need
Vaswani et al.
NIPS 2017
```

**Command**:

```cmd
onecite process references.txt --output results.bib --quiet
```

**Output**:

```
✅ Results saved to: results.bib

📊 Processing Report:
   Total entries: 2
   Successfully processed: 2
   Failed entries: 0
```

**Generated** (`results.bib`):

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
}

@inproceedings{Vaswani2017Attention,
  arxiv = "1706.03762",
  title = "Attention Is All You Need",
  author = "Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N. and Kaiser, Lukasz and Polosukhin, Illia",
  year = 2017,
  journal = "arXiv preprint",
  url = "https://arxiv.org/abs/1706.03762",
  abstract = "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train..."
}
```

---

## 💡 Advanced Usage

<details>
<summary><strong>🎨 Multiple Output Formats</strong></summary>

```cmd
:: APA format
onecite process refs.txt --output-format apa
:: → LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.
:: → Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017).
::   Attention is all you need. In Advances in Neural Information Processing Systems (pp. 5998-6008).

:: BibTeX format (default)
onecite process refs.txt --output-format bibtex

:: MLA format
onecite process refs.txt --output-format mla
:: → LeCun, Yann, Yoshua Bengio, and Geoffrey Hinton. "Deep Learning." Nature 521.7553 (2015): 436-444.
:: → Vaswani, Ashish, et al. "Attention Is All You Need." Advances in Neural Information Processing Systems. 2017.
```

</details>

<details>
<summary><strong>🤖 Interactive Mode</strong></summary>

```cmd
onecite process ambiguous.txt --interactive
```

**Example interaction:**

```
Found multiple possible matches for "Deep learning Hinton":
1. Deep learning
   Authors: LeCun, Yann; Bengio, Yoshua; Hinton, Geoffrey
   Journal: Nature
   Year: 2015
   Match Score: 92.5
   DOI: 10.1038/nature14539

2. Deep belief networks
   Authors: Hinton, Geoffrey E.
   Journal: Scholarpedia
   Year: 2009
   Match Score: 78.3
   DOI: 10.4249/scholarpedia.5947

Please select (1-2, 0=skip): 1
✅ Selected: Deep learning
```

</details>

<details>
<summary><strong>🐍 Python API</strong></summary>

```python
from onecite import process_references

def callback(candidates):
    return 0  # Select first candidate

result = process_references(
    input_content="Deep learning review\nLeCun, Bengio, Hinton\nNature 2015",
    input_type="txt",
    template_name="journal_article_full",
    output_format="bibtex",
    interactive_callback=callback
)

print(f"Processed: {result['report']['succeeded']} entries")
```

</details>

<details>
<summary><strong>📑 Supported Paper Types</strong></summary>

**Journal Articles with DOI:**

```text
10.1038/nature14539
```

→ Automatically fetches complete metadata from CrossRef

**Conference Papers:**

```text
Attention is all you need
Vaswani et al.
NIPS 2017
```

→ Recognizes conference venues (NIPS/NeurIPS, CVPR, ICML, etc.)
→ Generates `@inproceedings` BibTeX entries

**arXiv Papers:**

```text
1706.03762
```

→ Fetches metadata from arXiv API
→ Includes abstract and all authors

**Papers with URLs:**

```text
https://arxiv.org/abs/1706.03762
```

→ Extracts identifiers from URLs
→ Supports arXiv, DOI, and conference paper URLs

</details>

---

## ⚙️ Configuration

<details>
<summary><strong>📋 Command Line Options</strong></summary>

| Option            | Description                            | Default                |
| ----------------- | -------------------------------------- | ---------------------- |
| `--input-type`    | Input format (`txt`, `bib`)            | `txt`                  |
| `--output-format` | Output format (`bibtex`, `apa`, `mla`) | `bibtex`               |
| `--template`      | Template to use                        | `journal_article_full` |
| `--interactive`   | Enable interactive mode                | `False`                |
| `--quiet`         | Suppress verbose logging               | `False`                |
| `--output`, `-o`  | Output file path                       | `stdout`               |

**Examples:**

```cmd
:: Basic processing
onecite process input.txt

:: With custom options
onecite process input.bib --input-type bib --template conference_paper --output results.bib

:: Interactive mode with APA output
onecite process mixed.txt --interactive --output-format apa
```

</details>

---

## 🎨 Template System

Create custom template `my_template.yaml`:

```yaml
name: my_template
entry_type: "@article"
fields:
  - name: author
    required: true
  - name: title
    required: true
  - name: journal
    required: true
  - name: year
    required: true
  - name: doi
    required: false
    source_priority: [crossref_api]
```

Usage:

```cmd
onecite process refs.txt --template my_template
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**onecite** — Making citation management simple and accurate ✨

[⭐ Star](https://github.com/HzaCode/onecite) • [📖 Docs](https://onecite.readthedocs.io) • [🐛 Issues](https://github.com/HzaCode/onecite/issues) • [💬 Discussions](https://github.com/HzaCode/onecite/discussions)

</div>

