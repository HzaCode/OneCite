Basic Usage
===========

Command-Line Interface
----------------------

The main command for OneCite is::

    onecite process <input_file> [OPTIONS]

Supported Input Formats
~~~~~~~~~~~~~~~~~~~~~~~

**Plain Text (.txt)**

A text file where each reference is separated by a **blank line**::

    10.1038/nature14539

    Vaswani et al., 2017, Attention is all you need

    Smith (2020) Neural Architecture Search

.. note::

   Each entry must be separated by at least one blank line. Adjacent lines
   within the same block are treated as a single entry.

**BibTeX (.bib)**

Standard BibTeX format files::

    @article{LeCun2015,
        title = {Deep Learning},
        author = {LeCun, Yann and others},
        journal = {Nature},
        year = {2015}
    }

Supported Input Formats (Identifiers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite can process various academic identifiers:

- **DOI** - Digital Object Identifier (e.g., ``10.1038/nature14539``)
- **arXiv ID** - arXiv preprint identifier (e.g., ``2103.00020``)
- **PMID** - PubMed ID (e.g., ``12345678``)
- **ISBN** - International Standard Book Number (e.g., ``978-0-262-03384-8``)
- **GitHub URL** - Software repository (e.g., ``https://github.com/user/repo``)
- **Zenodo DOI** - Open research data (e.g., ``10.5281/zenodo.3233118``)
- **Plain Text** - Author name, title, or mixed reference (e.g., ``Deep learning, LeCun, 2015``)

Output Formats
~~~~~~~~~~~~~~

**BibTeX (.bib)** - The output format::

    onecite process refs.txt -o output.bib

Command-Line Options
~~~~~~~~~~~~~~~~~~~~~

**Output File (-o, --output)**::

    onecite process input.txt -o output.bib

**Output Format (--output-format)**::

    onecite process input.txt --output-format bibtex  # only supported format

**Interactive Mode (--interactive)**

When multiple potential matches are found, OneCite will prompt you to select the correct one::

    onecite process input.txt --interactive

Example interaction::

    Found multiple matches for "Deep learning Hinton":
    
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

**Quiet Mode (--quiet)**

Suppress verbose output::

    onecite process input.txt --quiet

**Google Scholar (--google-scholar)**

Enable Google Scholar as an additional data source (requires the optional ``scholarly`` package)::

    onecite process input.txt --google-scholar

**Direct String Input**

Pass a reference string directly instead of a file::

    onecite process "10.1038/nature14539"
    onecite process "Attention is all you need, Vaswani et al., NIPS 2017"

**Stdin Input**

Read from standard input using ``-``::

    echo "10.1038/nature14539" | onecite process -

**Help (--help)**

Display help information::

    onecite --help
    onecite process --help

Practical Examples
------------------

Example 1: Process a BibTeX File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    onecite process my_references.bib -o clean_references.bib --quiet

This will read ``my_references.bib``, enhance the entries, and save to ``clean_references.bib``.
The ``--input-type`` flag is optional for ``.bib`` files — OneCite detects the format automatically.

Example 2: Interactive Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    onecite process ambiguous.txt --interactive

This will allow you to manually verify and select the correct match for each reference.

Example 3: Quick Check Without Saving
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    onecite process references.txt --quiet

This will show you the processed results without saving to a file.

Example Files
-------------

Ready-to-use example input files are in ``docs/examples/``:

- ``references.txt`` — mixed identifiers and text queries (one entry per blank-separated block)
- ``existing.bib`` — a BibTeX file to be enriched

To run them::

    onecite process docs/examples/references.txt -o results.bib
    onecite process docs/examples/existing.bib -o enriched.bib

Next Steps
----------

- See :doc:`advanced_usage` for more complex scenarios
- Learn about :doc:`templates` to customize output format
- Check :doc:`python_api` to use OneCite in your Python code
