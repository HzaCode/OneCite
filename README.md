<!-- mcp-name: io.github.HzaCode/onecite -->

<div align="center">

<!-- Logo -->
<p align="center">
  <img src="https://github.com/HzaCode/OneCite/raw/master/logo_.jpg" alt="OneCite Logo" width="140" />
</p>

# OneCite 
### The Universal Citation & Academic Reference Toolkit
<p align="center">
  <a href="https://github.com/egeerardyn/awesome-LaTeX?tab=readme-ov-file#bibliography-tools">
    <img src="https://img.shields.io/badge/Awesome-LaTeX-blue.svg" alt="Awesome LaTeX"/>
  </a>
  <a href="https://pepy.tech/project/onecite">
    <img src="https://static.pepy.tech/badge/onecite" alt="Total Downloads"/>
  </a>
  <a href="https://pypi.org/project/onecite/">
    <img src="https://img.shields.io/pypi/v/onecite?color=306998&logo=pypi" alt="PyPI Version"/>
  </a>
  <a href="https://www.python.org">
    <img src="https://img.shields.io/badge/Python-3.7%2B-blue?logo=python" alt="Python Version"/>
  </a>
  <a href="https://registry.modelcontextprotocol.io/v0/servers?search=io.github.HzaCode/onecite">
    <img src="https://img.shields.io/badge/MCP-Registry-blue?logo=modelcontextprotocol" alt="MCP Registry"/>
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"/>
  </a>
  <img src="https://img.shields.io/badge/Status-Alpha-orange.svg" alt="Project Status"/>
</p>



**Effortlessly convert messy, unstructured references into perfectly formatted, standardized citations.**

OneCite is a powerful command-line tool and Python library designed to automate the tedious process of citation management. Feed it anything—DOIs, paper titles,arXiv IDs, or even a mix—and get clean, accurate bibliographic entries in return.

> **🚀 OneCite for Web is coming.**
>
> Dropping soon at **[hezhiang.com/onecite](http://hezhiang.com/onecite)**.

[✨ Features](#-features) • [🚀 Quick Start](#-quick-start) • [📖 Advanced Usage](#-advanced-usage) • [🤖 AI Integration](#-ai-assistant-integration-mcp) • [⚙️ Configuration](#️-configuration) • [🤝 Contributing](#-contributing)

---

</div>

## ✨ Features

- 🔍 **Smart Recognition**: Fuzzy matching against multiple academic databases to find references from incomplete or inaccurate information
- 📚 **Universal Format Support**: Input `.txt`/`.bib` → Output **BibTeX**, **APA**, or **MLA**
- 🎯 **High-Accuracy Pipeline**: 4-stage processing (clean → query → validate → format) ensures quality output
- 🤖 **Auto-Completion**: Automatically fills missing data (journal, volume, pages, ISBN, authors)
- 🎓 **7+ Citation Types**: Journal articles, conference papers, books, software, datasets, theses, preprints
- 🧠 **Intelligent Routing**: Auto-detects content type and domain (medical/CS/general) for optimal data retrieval
- 📄 **Universal Identifiers**: DOI, PMID, arXiv ID, ISBN, GitHub URL, Zenodo DOI, or plain text
- 🎛️ **Interactive Mode**: Manual selection when multiple matches found
- ⚙️ **Customizable Templates**: YAML-based template system for complete output control

## 🌐 Data Sources

<div align="center">

[![CrossRef](https://img.shields.io/badge/CrossRef-B31B1B?style=for-the-badge&logo=crossref&logoColor=white)](https://www.crossref.org/)
[![Semantic](https://img.shields.io/badge/Semantic-1857B6?style=for-the-badge&logo=semanticscholar&logoColor=white)](https://www.semanticscholar.org/)
[![OpenAlex](https://img.shields.io/badge/OpenAlex-FF6B35?style=for-the-badge&logo=openalex&logoColor=white)](https://openalex.org/)
[![PubMed](https://img.shields.io/badge/PubMed-326599?style=for-the-badge&logo=pubmed&logoColor=white)](https://pubmed.ncbi.nlm.nih.gov/)
[![dblp](https://img.shields.io/badge/dblp-002B5B?style=for-the-badge&logo=dblp&logoColor=white)](https://dblp.org/)
[![arXiv](https://img.shields.io/badge/𝒳_arXiv-B31B1B?style=for-the-badge)](https://arxiv.org/)
[![DataCite](https://img.shields.io/badge/DataCite-00B4A0?style=for-the-badge&logo=datacite&logoColor=white)](https://datacite.org/)
[![Zenodo](https://img.shields.io/badge/Zenodo-0A0E4A?style=for-the-badge&logo=zenodo&logoColor=white)](https://zenodo.org/)
[![Google](https://img.shields.io/badge/Google-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://books.google.com/)

</div>

## 🚀 Quick Start

Get up and running with OneCite in under a minute.

### Installation

```bash
# Recommended: Install from PyPI
pip install onecite
```

### Basic Usage

1.  **Create an input file** (`references.txt`) with mixed citation types:

    ```text
    10.1038/nature14539
    
    Attention is all you need, Vaswani et al., NIPS 2017
    
    Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.
    
    https://github.com/tensorflow/tensorflow
    
    10.5281/zenodo.3233118
    
    arXiv:2103.00020
    
    Smith, J. (2020). Neural Architecture Search. PhD Thesis. Stanford University.
    ```

2.  **Run the command**:

    ```bash
    onecite process references.txt -o results.bib --quiet
    ```

3.  **Get perfectly formatted output** (`results.bib`) with 7 different types:

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

@book{Goodfellow2016Deep,
  title = "Deep Learning",
  author = "Ian Goodfellow and Yoshua Bengio and Aaron Courville",
  publisher = "MIT Press",
  year = 2016,
  isbn = "9780262337373",
  url = "https://play.google.com/store/books/details?id=omivDQAAQBAJ&source=gbs_api",
  pages = "801",
}

@software{tensorflow2015tensorflow,
  title = "tensorflow",
  author = "tensorflow",
  publisher = "GitHub",
  year = 2015,
  version = "2.20.0",
  url = "https://github.com/tensorflow/tensorflow",
}

@misc{Brett2019nipynibabel,
  title = "nipy/nibabel: 2.4.1",
  author = "Brett, Matthew and Markiewicz, Christopher J. and Hanke, Michael and Côté, Marc-Alexandre and Cipollini, Ben and McCarthy, Paul and Cheng, Christopher P. and Halchenko, Yaroslav O. and Cottaar, Michiel and Ghosh, Satrajit and Larson, Eric and Wassermann, Demian and Gerhard, Stephan and Lee, Gregory R. and Kastman, Erik and Rokem, Ariel and Madison, Cindee and Morency, Félix C. and Moloney, Brendan and Burns, Christopher and Millman, Jarrod and Gramfort, Alexandre and Leppäkangas, Jaakko and Markello, Ross and van den Bosch, Jasper J.F. and Vincent, Robert D. and Subramaniam, Krish and Raamana, Pradeep Reddy and Nichols, B. Nolan and Baker, Eric M. and Goncalves, Mathias and Hayashi, Soichi and Pinsard, Basile and Haselgrove, Christian and Hymers, Mark and Koudoro, Serge and Oosterhof, Nikolaas N. and Amirbekian, Bago and Nimmo-Smith, Ian and Nguyen, Ly and Reddigari, Samir and St-Jean, Samuel and Garyfallidis, Eleftherios and Varoquaux, Gael and Kaczmarzyk, Jakub and Legarreta, Jon Haitz and Hahn, Kevin S. and Hinds, Oliver P. and Fauber, Bennet and Poline, Jean-Baptiste and Stutters, Jon and Jordan, Kesshi and Cieslak, Matthew and Moreno, Miguel Estevan and Haenel, Valentin and Schwartz, Yannick and Thirion, Bertrand and Papadopoulos Orfanos, Dimitri and Pérez-García, Fernando and Solovey, Igor and Gonzalez, Ivan and Lecher, Justin and Leinweber, Katrin and Raktivan, Konstantinos and Fischer, Peter and Gervais, Philippe and Gadde, Syam and Ballinger, Thomas and Roos, Thomas and Reddam, Venkateswara Reddy and freec84",
  year = 2019,
  howpublished = "Zenodo",
  url = "https://zenodo.org/record/3233118",
  version = "2.4.1",
  doi = "10.5281/zenodo.3233118",
}

@article{Radford2021Learning,
  arxiv = "2103.00020",
  title = "Learning Transferable Visual Models From Natural Language Supervision",
  author = "Radford, Alec and Kim, Jong Wook and Hallacy, Chris and Ramesh, Aditya and Goh, Gabriel and Agarwal, Sandhini and Sastry, Girish and Askell, Amanda and Mishkin, Pamela and Clark, Jack and Krueger, Gretchen and Sutskever, Ilya",
  year = 2021,
  journal = "arXiv preprint",
  url = "https://arxiv.org/abs/2103.00020",
}

@phdthesis{Smith2020Neural,
  title = "Neural Architecture Search",
  author = "Smith, J.",
  school = "Stanford University",
  year = 2020,
  type = "phdthesis",
}
```

</details>

## 📖 Advanced Usage

<details>
<summary><strong>🎨 Multiple Output Formats (APA, MLA)</strong></summary>

```bash
# Generate APA formatted citations
onecite process refs.txt --output-format apa
# → LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.
# → Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. In Advances in Neural Information Processing Systems.

# Generate MLA formatted citations
onecite process refs.txt --output-format mla
# → LeCun, Yann, Yoshua Bengio, and Geoffrey Hinton. "Deep Learning." Nature 521.7553 (2015): 436-444.
# → Vaswani, Ashish, et al. "Attention Is All You Need." Advances in Neural Information Processing Systems. 2017.
```
</details>

<details>
<summary><strong>🤖 Interactive Disambiguation</strong></summary>

For ambiguous entries, use the `--interactive` flag to ensure accuracy.

**Command**:
```bash
onecite process ambiguous.txt --interactive
```

**Example Interaction**:
```Found multiple possible matches for "Deep learning Hinton":
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
<summary><strong>🐍 Use as a Python Library</strong></summary>

Integrate OneCite's processing power directly into your Python scripts.

```python
from onecite import process_references

# Define a callback for non-interactive selection (e.g., always choose the best match)
def auto_select_callback(candidates):
    return 0

result = process_references(
    input_content="Deep learning review\nLeCun, Bengio, Hinton\nNature 2015",
    input_type="txt",
    output_format="bibtex",
    interactive_callback=auto_select_callback
)

print(result['output_content'])
```
</details>

<details>
<summary><strong>📑 Supported Input Examples</strong></summary>

```text
# DOI
10.1038/nature14539

# Conference Papers
Attention is all you need, Vaswani et al., NIPS 2017

# arXiv
1706.03762
https://arxiv.org/abs/1706.03762

# Books
Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.
Russell, S., & Norvig, P. (2021). Artificial Intelligence. ISBN: 978-0-13-604259-4.

# Software
https://github.com/tensorflow/tensorflow

# Datasets
10.5281/zenodo.3233118

# Thesis
Smith, J. (2020). Deep Learning for Computer Vision. PhD Thesis. MIT.

# PubMed
PMID: 27225100
```

</details>



## 🤖 AI Assistant Integration (MCP)

OneCite provides complete Model Context Protocol (MCP) support, enabling AI assistants to directly use OneCite's functionality for literature search, processing, and formatting.

<details>
<summary><strong>🚀 Setup & Configuration</strong></summary>

### Installation & Testing

```bash
# Install OneCite (includes MCP server)
pip install onecite

# Test MCP server
onecite-mcp
```

### Configure AI Assistant

#### For Claude Desktop
Edit `claude_desktop_config.json`:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "onecite": {
      "command": "onecite-mcp"
    }
  }
}
```

#### For Cursor
Add to `.cursor/settings.json`:

```json
{
  "mcpServers": {
    "onecite": {
      "command": "onecite-mcp"
    }
  }
}
```

Restart your editor to enable OneCite integration.

> 📖 For detailed MCP setup instructions, see [MCP_DEPLOYMENT.md](MCP_DEPLOYMENT.md)

### Available Functions

- **`cite`** - Generate single citations (DOI, titles, arXiv IDs → APA/MLA/BibTeX)
- **`batch_cite`** - Process multiple references at once
- **`search`** - Search academic literature by keywords

### Usage Examples

After configuration, tell your AI assistant:
- "Generate an APA citation for DOI: 10.1038/nature14539"
- "Batch process these references in BibTeX format"
- "Search for papers on machine learning"

</details>

## ⚙️ Configuration

<details>
<summary><strong>📋 Command Line Options</strong></summary>

| Option          | Description                               | Default                |
| --------------- | ----------------------------------------- | ---------------------- |
| `--input-type`  | Input format (`txt`, `bib`)               | `txt`                  |
| `--output-format` | Output format (`bibtex`, `apa`, `mla`)    | `bibtex`               |
| `--template`    | Specify a custom template YAML to use     | `journal_article_full` |
| `--interactive` | Enable interactive mode for disambiguation| `False`                |
| `--quiet`       | Suppress verbose logging                  | `False`                |
| `--output`, `-o`| Path to the output file                   | `stdout`               |
</details>

<details>
<summary><strong>🎨 Custom Templates</strong></summary>

Define custom output formats using a simple YAML template.

**Example `my_template.yaml`**:
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

**Usage**:
```bash
onecite process refs.txt --template my_template.yaml
```
</details>


## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and instructions on how to submit pull requests.

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---
<div align="center">

**OneCite: The all-in-one toolkit for every academic reference.** ✨

[⭐ Star on GitHub](https://github.com/HzaCode/OneCite) • [🚀 Try the Web App](http://hezhiang.com/onecite) • [📖 Read the Docs](https://onecite.readthedocs.io) • [🐛 Report an Issue](https://github.com/HzaCode/OneCite/issues) • [💬 Start a Discussion](https://github.com/HzaCode/OneCite/discussions)

</div>
