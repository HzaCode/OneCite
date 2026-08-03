Advanced Usage
==============

Reviewing Candidates for Ambiguous References
---------------------------------------------

``onecite process`` generally resolves supported identifiers (DOI, PMID,
arXiv ID, ISBN, and URLs) and never fuzzy-matches an ordinary ambiguous
plain-text reference. Explicitly labelled thesis/dissertation citations are a
documented exception: they use the OpenAIRE/BASE route and can fall back to
fields parsed from the input. To inspect candidate matches for any other messy
or incomplete reference, use ``onecite suggest``::

    onecite suggest "deep learning hinton 2015"

Candidates are returned for human review (with match scores and sources) and
are not promoted to source-resolved bibliography output. Add ``--json`` for a
machine-readable envelope.

Batch Processing Multiple Files
--------------------------------

Process multiple files sequentially::

    for file in *.txt; do
        onecite process "$file" -o "${file%.txt}.bib"
    done

Working with Different Data Sources
------------------------------------

Routing depends on the input; OneCite does **not** query every source for every
reference. For example, a DOI goes to Crossref and conditional fallbacks, a
PMID goes to NCBI, an ISBN-bearing entry goes to Google Books, and an arXiv ID
goes to arXiv. ``suggest`` is broader: Crossref, Semantic Scholar, and arXiv
are consulted for each usable query, with PubMed, Google Books, OpenAIRE/BASE,
and Google Scholar used only under documented conditions::

    onecite process references.txt

These are outbound requests. See :doc:`external_services` before using
confidential or embargoed input; that page lists what each route sends and
which source-health signals are (and are not) available.

Custom Templates
----------------

OneCite uses YAML-based templates to declare fields and supply fallback entry
types. Templates do not select the serialized output format. See
:doc:`templates` for details.

Working with Large Reference Lists
-----------------------------------

OneCite processes entries sequentially. ``--quiet`` suppresses logging but
does not make network calls faster. Use it when concise output is useful::

    onecite process large_file.txt --quiet -o output.bib

Memory-Efficient Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For long jobs, split input into recoverable chunks and retain the JSON report.
Choose chunk size based on the selected routes and provider behavior rather
than a fixed reference-count rule:

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

If OneCite cannot resolve an entry, it reports that entry and continues. Use
JSON plus the strict exit-code option to distinguish unresolved identifiers,
ambiguous text, and source errors::

    onecite process references.txt --json --fail-on-unresolved

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

- Explore :doc:`templates` for field declarations and fallback entry types
- Review :doc:`external_services` for network, privacy, and reproducibility boundaries
- Check :doc:`api/core` for complete API reference
- See :doc:`faq` for common questions
