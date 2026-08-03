OneCite - Auditable Citation Normalization
============================================

.. image:: https://img.shields.io/pypi/v/onecite?color=306998&logo=pypi&style=flat-square
   :target: https://pypi.org/project/onecite/
   :alt: PyPI Version

.. image:: https://img.shields.io/badge/Python-3.10+-blue?logo=python&style=flat-square
   :target: https://www.python.org
   :alt: Python Version

.. image:: https://img.shields.io/badge/License-MIT-green.svg?style=flat-square
   :target: https://github.com/HzaCode/OneCite/blob/main/LICENSE
   :alt: License

**OneCite** is a command-line tool and Python library for auditable citation
normalization. It routes strong identifiers such as DOIs, PMIDs, arXiv IDs,
ISBNs, GitHub URLs, and data DOIs to applicable metadata services. Ordinary
plain-text title searches are handled by ``onecite suggest`` as candidates for
review; explicitly labelled thesis citations have a separate documented route.

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
   external_services
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

- **Candidate Suggestions** - Search incomplete references with ``onecite suggest`` without promoting them to resolved bibliography output
- **BibTeX and CSL-JSON Output** - Emit ``.bib`` or structured citation records
- **4-stage Pipeline** - 4-stage process for consistent output
- **Field Completion** - Enrich entries with missing metadata
- 🎓 **7+ Citation Types** - Handles journal articles, conference papers, books, software, datasets, theses, and preprints
- **Many Identifier Types** - DOI, PMID, arXiv ID, ISBN, GitHub URLs, Zenodo DOI, and DataCite DOI

Data Sources
============

OneCite uses input-dependent routes across multiple scholarly metadata
sources; it does not query every source for every reference. See
:doc:`external_services` for the exact routes, transmitted data, privacy
boundary, and offline behavior.

- `CrossRef <https://www.crossref.org/>`_ - Academic publication metadata
- `Semantic Scholar <https://www.semanticscholar.org/>`_ - Literature search
- `PubMed <https://pubmed.ncbi.nlm.nih.gov/>`_ - Biomedical literature
- `arXiv <https://arxiv.org/>`_ - Preprint repository
- `DataCite <https://datacite.org/>`_ - Scientific datasets
- `Zenodo <https://zenodo.org/>`_ - Open research data
- `Google Books <https://books.google.com/>`_ - Book metadata
- `OpenAIRE <https://www.openaire.eu/>`_ / `BASE <https://www.base-search.net/>`_ - Theses & grey literature
- `GitHub <https://github.com/>`_ - Software repositories
- Google Scholar (optional scraping-based ``suggest`` fallback, off by default)

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
