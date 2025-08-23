
<div align="center">

<!-- Logo -->
<p align="center">
  <img src="logo_.jpg" alt="OneCite Logo" width="140" />
</p>

# OneCite 
### The Universal Citation & Academic Reference Toolkit

[![PyPI version](https://img.shields.io/pypi/v/onecite.svg)](https://pypi.org/project/onecite/)
[![Python Version](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Project Status](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

**Effortlessly convert messy, unstructured references into perfectly formatted, standardized citations.**

OneCite is a powerful command-line tool and Python library designed to automate the tedious process of citation management. Feed it anything—DOIs, paper titles,arXiv IDs, or even a mix—and get clean, accurate bibliographic entries in return.

[✨ Features](#-features) • [🚀 Quick Start](#-quick-start) • [📖 Advanced Usage](#-advanced-usage) • [🤖 MCP Integration](#-ai-assistant-integration-mcp) • [🤝 Contributing](#-contributing)

---

</div>

## ✨ Features

OneCite is packed with features to streamline your entire academic workflow, from initial search to final formatting.

- 🔍 **Smart Recognition**: Utilizes fuzzy matching against CrossRef and Google Scholar APIs to find the correct reference even from incomplete or slightly inaccurate information.
- 📚 **Universal Format Support**: Accepts `.txt` and `.bib` inputs and can output to **BibTeX**, **APA**, and **MLA** formats, adapting to any project's requirements.
- 🎯 **High-Accuracy Refinement**: A 4-stage processing pipeline cleans, queries, validates, and formats your entries to ensure the highest quality output.
- 🤖 **Intelligent Auto-Completion**: Automatically discovers and fills in missing bibliographic data like journal, volume, pages, and author lists.
- 🎛️ **Interactive Mode**: When multiple potential matches are found, an interactive prompt lets you choose the correct entry, giving you full control over ambiguous references.
- ⚙️ **Customizable Templates**: A flexible YAML-based template system allows for complete control over the output fields and their priority.
- 🎓 **Broad Paper Type Support**: Natively understands and processes journal articles, conference papers (NIPS, CVPR, ICML, etc.), and arXiv preprints with ease.
- 📄 **Seamless arXiv & URL Integration**: Automatically fetches metadata for arXiv IDs and can extract identifiers directly from `arxiv.org` or `doi.org` URLs.

## 🚀 Quick Start

Get up and running with OneCite in under a minute.

### Installation

```bash
# Recommended: Install from PyPI
pip install onecite

# Or, install from source for the latest version
git clone https://github.com/HzaCode/OneCite.git
cd OneCite
pip install -e .
```

### Basic Usage

1.  **Create an input file** (`references.txt`):

    ```text
    10.1038/nature14539
    
    Attention is all you need
    Vaswani et al.
    NIPS 2017
    ```

2.  **Run the command**:

    ```bash
    onecite process references.txt -o results.bib --quiet
    ```

3.  **Get perfectly formatted output** (`results.bib`):

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
      booktitle = "Advances in Neural Information Processing Systems",
      year = 2017,
      url = "https://arxiv.org/abs/1706.03762",
    }
    ```

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
<summary><strong>📑 Supported Input Types</strong></summary>

OneCite is designed to be flexible and understands various common academic identifiers.

-   **DOI**: `10.1038/nature14539`
-   **Conference Papers**: `Attention is all you need, Vaswani et al., NIPS 2017`
-   **arXiv ID**: `1706.03762`
-   **URLs**: `https://arxiv.org/abs/1706.03762`

</details>


## 🤖 MCP Integration

Integrate OneCite with your favorite MCP client via the Model Context Protocol (MCP) to let your automation manage and generate citations for you.

### Configuration

To enable this feature, add the following configuration to your automation-powered editor's `settings.json` file. This requires manual configuration.

```json
{
  "mcpServers": {
    "onecite": {
      "command": "onecite-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

After adding the configuration and restarting your editor, the MCP client will gain the ability to use OneCite's tools (`cite`, `batch_cite`, `search`) directly within the chat.

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

**Usage**:```bash
onecite process refs.txt --template my_template.yaml```
</details>

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and instructions on how to submit pull requests.

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---
<div align="center">

**OneCite** - Simple, Accurate, and Powerful Citation Management ✨

[⭐ Star on GitHub](https://github.com/HzaCode/OneCite) • [📖 Read the Docs](https://onecite.readthedocs.io) • [🐛 Report an Issue](https://github.com/HzaCode/OneCite/issues) • [💬 Start a Discussion](https://github.com/HzaCode/OneCite/discussions)

</div>
```
