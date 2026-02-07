Quick Start Guide
=================

This guide walks through a basic OneCite workflow.

1. Installation
---------------

First, install OneCite using pip::

    pip install onecite

2. Create Your Input File
--------------------------

Create a file named ``references.txt`` with your mixed-format references.

Add blank lines between entries to avoid misidentification.

Example ``references.txt``::

    10.1038/nature14539

    Attention is all you need, Vaswani et al., NIPS 2017

    Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.

    https://github.com/tensorflow/tensorflow

    10.5281/zenodo.3233118

    arXiv:2103.00020

    Smith, J. (2020). Neural Architecture Search. PhD Thesis. Stanford University.

3. Process Your References
---------------------------

Run OneCite to process your file::

    onecite process references.txt -o results.bib --quiet

The ``--quiet`` flag suppresses verbose output. Remove it if you want to see processing details.

4. View Your Results
--------------------

Your ``results.bib`` file now contains entries in BibTeX format::

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

Common Command-Line Options
----------------------------

**Output Formats**::

    onecite process refs.txt --output-format apa
    
    onecite process refs.txt --output-format mla

**Interactive Mode**::

    # Use interactive mode for ambiguous entries
    onecite process refs.txt --interactive

**Batch Processing**::

    # Process BibTeX file
    onecite process input.bib -o output.bib

For more advanced usage, see :doc:`advanced_usage`.

Using OneCite as a Python Library
----------------------------------

You can also use OneCite directly in your Python scripts::

    from onecite import process_references
    
    result = process_references(
        input_content="Deep learning review\nLeCun, Bengio, Hinton\nNature 2015",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0  # Auto-select first match
    )
    
    # Print formatted citations
    for citation in result['results']:
        print(citation)
    
    # Check processing report
    print(f"\nProcessed {result['report']['succeeded']}/{result['report']['total']} entries")

For more details, see :doc:`python_api`.

Next Steps
----------

- Learn more about :doc:`advanced_usage`
- Check :doc:`templates` to customize output format
- See :doc:`api/core` for Python API reference
