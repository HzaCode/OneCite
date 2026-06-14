Advanced Usage
==============

Reviewing Candidates for Ambiguous References
---------------------------------------------

``onecite process`` only resolves strong identifiers (DOI, PMID, arXiv ID,
ISBN, URLs) and never guesses from an ambiguous plain-text reference. To
inspect candidate matches for a messy or incomplete reference, use
``onecite suggest``::

    onecite suggest "deep learning hinton 2015"

Candidates are returned for human review (with match scores and sources) and
are not emitted as verified BibTeX. Add ``--json`` for a machine-readable
envelope.

Batch Processing Multiple Files
--------------------------------

Process multiple files sequentially::

    for file in *.txt; do
        onecite process "$file" -o "${file%.txt}.bib"
    done

Working with Different Data Sources
------------------------------------

OneCite queries multiple data sources (CrossRef, PubMed, arXiv, Semantic Scholar, Google Books, and others) and selects the best match. All sources are tried for every reference — you do not need to configure routing manually::

    onecite process references.txt

Custom Templates
----------------

OneCite uses YAML-based templates for output formatting. See :doc:`templates` for detailed information.

Working with Large Reference Lists
-----------------------------------

For large files (100+ entries), use quiet mode to improve performance::

    onecite process large_file.txt --quiet -o output.bib

Memory-Efficient Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite processes references sequentially, so it should handle files with thousands of entries. If you encounter memory issues, split your input file:

::

    # Split into chunks
    split -l 100 large_file.txt chunk_
    
    # Process each chunk
    for chunk in chunk_*; do
        onecite process "$chunk" -o "${chunk}.bib"
    done

Error Handling and Recovery
----------------------------

Handling Failed Entries
~~~~~~~~~~~~~~~~~~~~~~~

If OneCite cannot process a reference, it will skip it and continue. Check the output for warnings.

**To debug specific entries**, process them individually::

    echo "your_reference_here" > test.txt
    onecite process test.txt

Combining Results
~~~~~~~~~~~~~~~~~

To merge multiple `.bib` files::

    cat file1.bib file2.bib file3.bib > combined.bib


Using with Git for Version Control
-----------------------------------

Track changes to your bibliography::

    git add references.txt results.bib
    git commit -m "Update bibliography with new papers"

This allows you to see exactly what changed in your citations over time.

Integration with LaTeX and Overleaf
-----------------------------------

1. Export your references to a `.bib` file::

    onecite process references.txt -o my_references.bib

2. In your LaTeX file, add::

    \bibliography{my_references}
    \bibliographystyle{plain}

3. Upload to Overleaf and you're done!

Python API Advanced Usage
--------------------------

For advanced Python usage, see :doc:`python_api`.

Next Steps
----------

- Explore :doc:`templates` for custom output formats
- Check :doc:`api/core` for complete API reference
- See :doc:`faq` for common questions
