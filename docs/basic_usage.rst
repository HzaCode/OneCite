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

    arXiv:1706.03762

    ISBN:9780262035613

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

**Automation-Friendly JSON (--json)**

Print a stable machine-readable envelope with results, counts, options,
and failed-entry details::

    onecite process input.txt --json

Use a strict exit code when any entry is unresolved::

    onecite process input.txt --json --fail-on-unresolved

**Streaming NDJSON (--ndjson)**

Print newline-delimited JSON events for automation that wants a summary
line followed by result and failure events::

    onecite process input.txt --ndjson

**Google Scholar (suggest only, --google-scholar)**

A best-effort fallback for the ``suggest`` command only (requires the optional
``scholarly`` package: ``pip install onecite[scholar]``). It is consulted only
when CrossRef and Semantic Scholar return nothing. Because it scrapes a service
with no public API, it is off by default, may be blocked by a CAPTCHA, and is
not guaranteed to be reproducible. It is never used by ``process``, whose output
is authoritative::

    onecite suggest input.txt --google-scholar

**Direct String Input**

Pass a reference string directly instead of a file::

    onecite process "10.1038/nature14539"
    onecite suggest "Attention is all you need, Vaswani et al., NIPS 2017"

**Stdin Input**

Read from standard input using ``-``::

    echo "10.1038/nature14539" | onecite process -

**Help (--help)**

Display help information::

    onecite --help
    onecite process --help

Template Discovery
~~~~~~~~~~~~~~~~~~

List the bundled fallback BibTeX templates and the fields they request::

    onecite templates

Use JSON output when another tool needs to inspect the same metadata::

    onecite templates --json

Benchmarking
~~~~~~~~~~~~

Run the bundled deterministic golden-case regression suite::

    onecite benchmark

Use JSON output for automation and regression checks::

    onecite benchmark --json

The command exits with ``0`` only when the configured pass-rate gate is met.
With the default gate, every bundled case must pass. By default it uses
bundled offline fixtures; add ``--live`` only when you want to spot-check real
external APIs. Passing the bundled suite means the covered cases passed; it is
not a comprehensive citation-accuracy or performance score.

Doctor
~~~~~~

Check the local OneCite installation and bundled regression resources::

    onecite doctor

Use JSON output when automation or CI needs a stable health envelope::

    onecite doctor --json

The doctor report checks package importability, templates, bundled
benchmark resources, the OneCite Skill file, and the offline benchmark
check.

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
