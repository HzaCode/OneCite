
<div align="center">

<p align="center">
  <img src="https://github.com/HzaCode/OneCite/raw/master/logo_.jpg" alt="OneCite Logo" width="160" />
</p>

# OneCite
### The Universal Citation & Academic Reference Toolkit

<p align="center">
  <a href="https://github.com/egeerardyn/awesome-LaTeX?tab=readme-ov-file#bibliography-tools">
    <img src="https://img.shields.io/badge/Recommended%20on-Awesome%20LaTeX-blueviolet?logo=awesome-lists&logoColor=white&style=flat-square" alt="Recommended on Awesome LaTeX">
  </a>
</p>

</div>

<p align="center">
    <strong>Effortlessly convert messy, unstructured references into perfectly formatted, standardized citations.</strong>
</p>

<div align="center">

[![Status](https://img.shields.io/badge/Status-Active-green.svg?style=flat-square)](https://github.com/HzaCode/OneCite)
[![PyPI Version](https://img.shields.io/pypi/v/onecite?color=306998&logo=pypi&style=flat-square)](https://pypi.org/project/onecite/)
[![Python Version](https://img.shields.io/badge/Python-3.7+-blue?logo=python&style=flat-square)](https://www.python.org)
[![Downloads](https://static.pepy.tech/badge/onecite?style=flat-square)](https://pepy.tech/project/onecite)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue?logo=modelcontextprotocol&style=flat-square)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.HzaCode/onecite)

</div>

<p align="center">
  <a href="#-features">✨ Features</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-advanced-usage">📖 Advanced Usage</a> •
  <a href="#-ai-assistant-integration-mcp">🤖 MCP Integration</a> •
  <a href="#-contributing">🤝 Contributing</a>
</p>

---

<p align="center">
  OneCite is a powerful command-line tool and Python library designed to automate the tedious process of citation management. Feed it anything—DOIs, paper titles, arXiv IDs, or even a mix—and get clean, accurate bibliographic entries in return.
</p>

> **🚀 OneCite for Web is coming soon at [hezhiang.com/onecite](http://hezhiang.com/onecite)**

---

## ✨ Features

| Feature                 | Description                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| 🔍 **Smart Recognition**    | Fuzzy matching against multiple academic databases to find references from incomplete or inaccurate info. |
| 📚 **Universal Formats**    | Input `.txt`/`.bib` → Output **BibTeX**, **APA**, or **MLA** formats with ease.                     |
| 🎯 **High-Accuracy Pipeline** | A 4-stage process (clean → query → validate → format) ensures the highest quality output.             |
| 🤖 **Auto-Completion**      | Automatically enriches entries by filling in missing data like journal, volume, pages, and authors.   |
| 🎓 **7+ Citation Types**    | Handles journal articles, conference papers, books, software, datasets, theses, and preprints.        |
| 🧠 **Intelligent Routing**  | Auto-detects content type and domain (Medical/CS/General) for optimal data retrieval.                 |
| 📄 **Universal Identifiers**| Accepts DOI, PMID, arXiv ID, ISBN, GitHub URL, Zenodo DOI, or even plain text queries.               |
| 🎛️ **Interactive Mode**    | Manually select the correct entry when multiple potential matches are found.                          |
| ⚙️ **Custom Templates**     | A YAML-based template system provides complete control over the final output format.                  |



## 🌐 Data Sources

<div align="center">

[![CrossRef](https://img.shields.io/badge/CrossRef-B31B1B?style=for-the-badge&logo=crossref&logoColor=white)](https://www.crossref.org/)
[![Semantic Scholar](https://img.shields.io/badge/Semantic-1857B6?style=for-the-badge&logo=semanticscholar&logoColor=white)](https://www.semanticscholar.org/)
[![OpenAlex](https://img.shields.io/badge/OpenAlex-FF6B35?style=for-the-badge&logo=openalex&logoColor=white)](https://openalex.org/)
[![PubMed](https://img.shields.io/badge/PubMed-326599?style=for-the-badge&logo=pubmed&logoColor=white)](https://pubmed.ncbi.nlm.nih.gov/)
[![dblp](https://img.shields.io/badge/dblp-002B5B?style=for-the-badge&logo=dblp&logoColor=white)](https://dblp.org/)
[![arXiv](https://img.shields.io/badge/𝒳_arXiv-B31B1B?style=for-the-badge)](https://arxiv.org/)
[![DataCite](https://img.shields.io/badge/DataCite-00B4A0?style=for-the-badge&logo=datacite&logoColor=white)](https://datacite.org/)
[![Zenodo](https://img.shields.io/badge/Zenodo-0A0E4A?style=for-the-badge&logo=zenodo&logoColor=white)](https://zenodo.org/)
[![Google Books](https://img.shields.io/badge/Google-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://books.google.com/)

</div>

## 🚀 Quick Start

Get up and running with OneCite in under a minute.

### 1. Installation
```bash
# Recommended: Install from PyPI
pip install onecite
```

### 2. Create an Input File
Create a file named `references.txt` with your mixed-format references:
```text
# references.txt
10.1038/nature14539
Attention is all you need, Vaswani et al., NIPS 2017
Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.
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

### 4. Get Perfectly Formatted Output
Your `results.bib` file now contains 7 perfectly formatted entries of different types.

<details>
<summary><strong>📄 View Complete Output (results.bib)</strong></summary>

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
}
@inproceedings{Vaswani2017Attention,
  arxiv = "1706.03762",
  title = "Attention Is All You Need",
  author = "Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N. and Kaiser, Lukasz and Polosukhin, Illia",
  year = 2017,
  journal = "arXiv preprint",
  url = "https://arxiv.org/abs/1706.03762",
}
# ... and 5 more entries ...
```

</details>

## 📖 Advanced Usage

<details>
<summary><strong>🎨 Multiple Output Formats (APA, MLA)</strong></summary>

```bash
# Generate APA formatted citations
onecite process refs.txt --output-format apa
# → LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.

# Generate MLA formatted citations
onecite process refs.txt --output-format mla
# → LeCun, Yann, Yoshua Bengio, and Geoffrey Hinton. "Deep Learning." Nature 521.7553 (2015): 436-444.
```
</details>

<details>
<summary><strong>🤖 Interactive Disambiguation</strong></summary>

For ambiguous entries, use the `--interactive` flag to manually select the correct match and ensure accuracy.

**Command**:
```bash
onecite process ambiguous.txt --interactive
```

**Example Interaction**:
```
Found multiple possible matches for "Deep learning Hinton":
1. Deep learning
   Authors: LeCun, Yann; Bengio, Yoshua; Hinton, Geoffrey
   Journal: Nature, 2015
   DOI: 10.1038/nature14539

2. Deep belief networks
   Authors: Hinton, Geoffrey E.
   Journal: Scholarpedia, 2009
   DOI: 10.4249/scholarpedia.5947

Please select (1-2, 0=skip): 1
✅ Selected: Deep learning
```
</details>

<details>
<summary><strong>🐍 Use as a Python Library</strong></summary>

Integrate OneCite's processing power directly into your Python scripts.

```python
from onecite import process_references

# A callback can be used for non-interactive selection (e.g., always choose the best match)
def auto_select_callback(candidates):
    return 0 # Index of the best candidate

result = process_references(
    input_content="Deep learning review\nLeCun, Bengio, Hinton\nNature 2015",
    input_type="txt",
    output_format="bibtex",
    interactive_callback=auto_select_callback
)

print(result['output_content'])
```
</details>


## 🤖 MCP Integration

OneCite provides complete Model Context Protocol (MCP) support, enabling MCP clients to directly use its functionality for literature search, processing, and formatting.

<details>
<summary><strong>🚀 Setup & Usage</strong></summary>

### 1. Installation & Testing

```bash
# Install OneCite (includes MCP server)
pip install onecite

# Test the MCP server
onecite-mcp
```

### 2. Configure Your automation Assistant

#### For MCP desktop client
Add the following to `claude_desktop_config.json`:
```json
{
  "mcpServers": { "onecite": { "command": "onecite-mcp" } }
}
```

#### For editor client
Add the following to `.cursor/settings.json`:
```json
{
  "mcpServers": { "onecite": { "command": "onecite-mcp" } }
}
```
Restart your editor to enable the integration.

### 3. Available Functions & Examples
- **`cite`**: Generate a single citation (e.g., *"Generate an APA citation for DOI: 10.1038/nature14539"*).
- **`batch_cite`**: Process a list of references (e.g., *"Batch process these references in BibTeX format"*).
- **`search`**: Search academic literature by keywords (e.g., *"Search for papers on machine learning"*).

</details>


## 🤝 Contributing

Contributions are always welcome! Please see [**CONTRIBUTING.md**](CONTRIBUTING.md) for development guidelines and instructions on how to submit a pull request.

## 📄 License

This project is licensed under the **MIT License**. See the [**LICENSE**](LICENSE) file for details.

---

<div align="center">

**OneCite: The all-in-one toolkit for every academic reference.**

<p>
  <a href="https://github.com/HzaCode/OneCite">⭐ Star on GitHub</a> •
  <a href="http://hezhiang.com/onecite">🚀 Try the Web App</a> •
  <a href="https://github.com/HzaCode/OneCite/issues">🐛 Report an Issue</a> •
  <a href="https://github.com/HzaCode/OneCite/discussions">💬 Start a Discussion</a>
</p>

</div>
