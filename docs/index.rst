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

**OneCite** is a command-line tool and Python library for citation management. It resolves strong identifiers such as DOIs, PMIDs, arXiv IDs, ISBNs, GitHub URLs, and data DOIs into formatted bibliographic entries. Plain-text title searches are handled by ``onecite suggest`` as candidate suggestions.

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
   benchmarking
   cli_contracts
   onecite_skill
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

- **Candidate Suggestions** - Search incomplete references with ``onecite suggest`` without resolving them to BibTeX
- **BibTeX Output** - Standards-compliant ``.bib`` files rendered with ``bibtexparser``
- **4-stage Pipeline** - 4-stage process for consistent output
- **Field Completion** - Enrich entries with missing metadata
- 🎓 **7+ Citation Types** - Handles journal articles, conference papers, books, software, datasets, theses, and preprints
- **Many Identifier Types** - DOI, PMID, arXiv ID, ISBN, GitHub URLs, Zenodo DOI, and DataCite DOI

Data Sources
============

OneCite integrates with multiple authoritative academic data sources:

- `CrossRef <https://www.crossref.org/>`_ - Academic publication metadata
- `Semantic Scholar <https://www.semanticscholar.org/>`_ - Literature search
- `PubMed <https://pubmed.ncbi.nlm.nih.gov/>`_ - Biomedical literature
- `arXiv <https://arxiv.org/>`_ - Preprint repository
- `DataCite <https://datacite.org/>`_ - Scientific datasets
- `Zenodo <https://zenodo.org/>`_ - Open research data
- `Google Books <https://books.google.com/>`_ - Book metadata
- `external providerRE <https://www.openaire.eu/>`_ / `BASE <https://www.base-search.net/>`_ - Theses & grey literature
- `GitHub <https://github.com/>`_ - Software repositories
- Google Scholar (optional ``suggest``-only best-effort fallback, via the ``scholarly`` package)

Quick Start
===========

Installation::

    pip install onecite

Create a ``references.txt`` file::

    10.1038/nature14539
    
    arXiv:1706.03762
    
    ISBN:9780262035613

Run OneCite::

    onecite process references.txt -o results.bib --quiet

For more information, see :doc:`quick_start`.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
