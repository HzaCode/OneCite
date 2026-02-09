OneCite - Citation & Academic Reference Toolkit
=================================================

.. image:: https://img.shields.io/pypi/v/onecite?color=306998&logo=pypi&style=flat-square
   :target: https://pypi.org/project/onecite/
   :alt: PyPI Version

.. image:: https://img.shields.io/badge/Python-3.10+-blue?logo=python&style=flat-square
   :target: https://www.python.org
   :alt: Python Version

.. image:: https://img.shields.io/badge/License-MIT-green.svg?style=flat-square
   :target: https://github.com/HzaCode/OneCite/blob/main/LICENSE
   :alt: License

**OneCite** is a command-line tool and Python library for citation management. It accepts DOIs, paper titles, arXiv IDs, and mixed inputs, and outputs formatted bibliographic entries.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quick_start
   basic_usage

.. toctree::
   :maxdepth: 2
   :caption: User Guides

   advanced_usage
   python_api
   templates
   output_formats

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/exceptions
   api/pipeline

.. toctree::
   :maxdepth: 2
   :caption: Additional Resources

   faq
   contributing
   changelog

Key Features
============

- **Fuzzy Matching** - Match references against multiple academic databases
- **Multiple Formats** - BibTeX, APA, and MLA output
- **4-stage Pipeline** - 4-stage process for consistent output
- **Field Completion** - Enrich entries with missing metadata
- 🎓 **7+ Citation Types** - Handles journal articles, conference papers, books, software, datasets, theses, and preprints
- **Many Identifier Types** - DOI, PMID, arXiv ID, ISBN, GitHub URLs, Zenodo DOI, or plain text queries

Data Sources
============

OneCite integrates with multiple authoritative academic data sources:

- `CrossRef <https://www.crossref.org/>`_ - Academic publication metadata
- `Semantic Scholar <https://www.semanticscholar.org/>`_ - AI-powered literature search
- `OpenAlex <https://openalex.org/>`_ - Open academic graph
- `PubMed <https://pubmed.ncbi.nlm.nih.gov/>`_ - Biomedical literature
- `DBLP <https://dblp.org/>`_ - Computer science bibliography
- `arXiv <https://arxiv.org/>`_ - Preprint repository
- `DataCite <https://datacite.org/>`_ - Scientific datasets
- `Zenodo <https://zenodo.org/>`_ - Open research data
- `Google Books <https://books.google.com/>`_ - Book metadata

Quick Start
===========

Installation::

    pip install onecite

Create a ``references.txt`` file::

    10.1038/nature14539
    
    Attention is all you need, Vaswani et al., NIPS 2017
    
    Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.

Run OneCite::

    onecite process references.txt -o results.bib --quiet

For more information, see :doc:`quick_start`.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
