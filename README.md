

<div align="center">
  <p align="center">
    <img src="https://github.com/HzaCode/OneCite/raw/master/logo_.jpg" alt="OneCite Logo" width="160" />
  </p>

  <h1>OneCite</h1>
  <h3>Citation & Academic Reference Toolkit</h3>
</div>

<div align="center">

[![Awesome CLI Apps](https://img.shields.io/badge/Featured-Awesome%20CLI%20Apps%2018.2k⭐-FF6B35?style=flat-square&logo=awesome-lists&logoColor=white)](https://github.com/agarrharr/awesome-cli-apps?tab=readme-ov-file#academia)

[![Tests](https://img.shields.io/github/actions/workflow/status/HzaCode/OneCite/tests.yml?style=flat-square&logo=github)](https://github.com/HzaCode/OneCite/actions)
[![codecov](https://img.shields.io/codecov/c/github/HzaCode/OneCite?style=flat-square&logo=codecov)](https://codecov.io/gh/HzaCode/OneCite)
[![PyPI](https://img.shields.io/pypi/v/onecite?style=flat-square&logo=pypi&color=blue)](https://pypi.org/project/onecite/)
[![Python](https://img.shields.io/badge/3.10+-blue?style=flat-square&logo=python)](https://www.python.org)
[![Downloads](https://img.shields.io/pepy/dt/onecite?style=flat-square)](https://pepy.tech/project/onecite)
[![MIT](https://img.shields.io/badge/MIT-green?style=flat-square)](LICENSE)
[![Docs](https://img.shields.io/badge/Docs-Pages-blue?style=flat-square&logo=github)](https://hzacode.github.io/OneCite/)
[![Awesome LaTeX](https://img.shields.io/badge/Awesome-LaTeX-008B8B?style=flat-square&logo=awesome-lists&logoColor=white&labelColor=493267)](https://github.com/egeerardyn/awesome-LaTeX?tab=readme-ov-file#bibliography-tools)


</div>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-advanced-usage">📖 Advanced Usage</a> •
  <a href="#-contributing">🤝 Contributing</a>
</p>

---

<p align="center">
  OneCite is a command-line tool and Python library for citation management. It accepts DOIs, paper titles, arXiv IDs, and mixed inputs, and outputs formatted bibliographic entries.
</p>

---

## Features

| Feature                 | Description                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| **Fuzzy Matching**          | Match references against multiple academic databases even from incomplete or inaccurate info.         |
| **Multiple Formats**        | Input `.txt`/`.bib` → Output **BibTeX**, **APA**, or **MLA**.                                         |
| **4-stage Pipeline**        | A 4-stage process (clean → query → validate → format) to produce consistent output.                  |
| **Field Completion**        | Enrich entries by filling in missing fields like journal, volume, pages, and authors.                |
| 🎓 **7+ Citation Types**    | Handles journal articles, conference papers, books, software, datasets, theses, and preprints.        |
| **Domain-Aware Routing**    | Auto-detects content type and domain (Medical/CS/General) to pick the best data source.              |
| **Many Identifier Types**   | Accepts DOI, PMID, arXiv ID, ISBN, GitHub URL, Zenodo DOI, or plain text queries.                    |
| 🎛️ **Interactive Mode**    | Manually select the correct entry when multiple potential matches are found.                          |
| **Custom Templates**        | YAML-based templates to control which fields are collected and how entries are typed.                 |


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
onecite process refs.txt --output-format apa
# → LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.

onecite process refs.txt --output-format mla
# → LeCun, Yann, Yoshua Bengio, and Geoffrey Hinton. "Deep Learning." Nature 521.7553 (2015): 436-444.
```
</details>

<details>
<summary><strong>Interactive Disambiguation</strong></summary>

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
Selected: Deep learning
```
</details>

<details>
<summary><strong>🐍 Use as a Python Library</strong></summary>

Use OneCite directly in your Python scripts.

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



## 🤝 Contributing

Contributions are always welcome! Please see [**CONTRIBUTING.md**](CONTRIBUTING.md) for development guidelines and instructions on how to submit a pull request.

## 📄 License

This project is licensed under the **MIT License**. See the [**LICENSE**](LICENSE) file for details.

### Disclosure

Development was assisted by standard productivity tools including Generative AI for streamlining implementation details. All output was verified and integrated by the maintainer, and **no LLMs are used by the package at runtime**.

---

<div align="center">

**OneCite**

<p>
  <a href="https://github.com/HzaCode/OneCite">Star on GitHub</a> •
  <a href="http://hezhiang.com/onecite">Web App</a> •
  <a href="https://github.com/HzaCode/OneCite/issues">🐛 Report an Issue</a> •
  <a href="https://github.com/HzaCode/OneCite/discussions">Discussions</a>
</p>

</div>
