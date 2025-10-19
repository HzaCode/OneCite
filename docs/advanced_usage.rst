Advanced Usage
==============

Interactive Disambiguation
---------------------------

When OneCite finds multiple potential matches for a reference, it can enter interactive mode to let you choose the correct one.

Enabling Interactive Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    onecite process ambiguous.txt --interactive

Example Session
~~~~~~~~~~~~~~~

::

    Processing ambiguous.txt...
    
    Found 2 matches for "Deep learning Hinton":
    
    1. Deep Learning
       Authors: Yann LeCun, Yoshua Bengio, Geoffrey Hinton
       Journal: Nature
       Year: 2015
       Volume: 521, Pages: 436-444
       DOI: 10.1038/nature14539
    
    2. Deep Belief Networks
       Authors: Geoffrey E. Hinton, Simon Osindero, Yee-Whye Teh
       Journal: Neural Computation
       Year: 2006
       Volume: 18, Pages: 1527-1554
       DOI: 10.1162/neco.2006.18.7.1527
    
    Please select (1-2, 0=skip): 1
    ✅ Selected: Deep Learning (10.1038/nature14539)

Batch Processing Multiple Files
--------------------------------

Process multiple files sequentially::

    for file in *.txt; do
        onecite process "$file" -o "${file%.txt}.bib"
    done

Working with Different Data Sources
------------------------------------

OneCite intelligently routes queries to appropriate data sources:

**For Biomedical Literature**

Add search terms related to medicine, biology, or health::

    onecite process medical_refs.txt

This will prioritize PubMed when available.

**For Computer Science**

Add search terms related to CS topics::

    onecite process cs_refs.txt

This will prioritize DBLP and arXiv.

**For General Academic Work**

Mixed references will use CrossRef and Semantic Scholar::

    onecite process general_refs.txt

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

Converting Between Formats
---------------------------

Convert BibTeX to APA::

    onecite process input.bib --output-format apa -o output.txt

Convert APA to BibTeX::

    # First save APA format in a parseable way, then convert back
    onecite process references.txt --output-format apa -o apa_refs.txt
    # Then process again to get BibTeX
    onecite process original.txt -o output.bib

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
- Learn :doc:`mcp_integration` for AI assistant usage
- Check :doc:`api/core` for complete API reference
- See :doc:`faq` for common questions
