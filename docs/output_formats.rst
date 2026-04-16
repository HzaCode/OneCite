Output Formats
==============

OneCite currently writes **BibTeX only**.  Earlier versions also advertised
APA and MLA output, but those renderers produced inconsistent results and
have been removed (see issues #31 and #32).  The CLI now rejects any
``--output-format`` other than ``bibtex``.

If you need APA or MLA output, run OneCite first to get a clean BibTeX
file and then pipe it through a dedicated renderer such as
`pandoc <https://pandoc.org/>`_, `citeproc-py <https://github.com/brechtm/citeproc-py>`_
or `bibtex2html <https://www.lri.fr/~filliatr/bibtex2html/>`_.

BibTeX Format
-------------

BibTeX is the standard format for LaTeX documents.

Format Specification
~~~~~~~~~~~~~~~~~~~~

::

    @article{LeCun2015Deep,
      doi = "10.1038/nature14539",
      title = "Deep Learning",
      author = "LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey",
      journal = "Nature",
      year = 2015,
      volume = 521,
      number = 7553,
      pages = "436-444",
      publisher = "Springer Science and Business Media LLC",
      url = "https://doi.org/10.1038/nature14539"
    }

Using BibTeX Format
~~~~~~~~~~~~~~~~~~~

::

    # Command line (bibtex is the default, the flag is optional)
    onecite process references.txt -o output.bib --output-format bibtex

    # Python API
    from onecite import process_references

    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )

    for citation in result['results']:
        print(citation)

Integration with LaTeX
~~~~~~~~~~~~~~~~~~~~~~

1. Save references to a ``.bib`` file using OneCite
2. In your LaTeX document::

    \documentclass{article}
    \begin{document}

    Some text citing \cite{LeCun2015Deep}.

    \bibliography{output}
    \bibliographystyle{plain}

    \end{document}

3. Compile with bibtex::

    pdflatex document.tex
    bibtex document
    pdflatex document.tex
    pdflatex document.tex

BibTeX Entry Types
~~~~~~~~~~~~~~~~~~

Common entry types produced by OneCite:

- ``@article`` - Journal article
- ``@inproceedings`` - Conference paper
- ``@book`` - Book
- ``@phdthesis`` - PhD thesis
- ``@mastersthesis`` - Master's thesis
- ``@misc`` - Miscellaneous
- ``@software`` - Software
- ``@dataset`` - Dataset

Tips
----

- Use consistent key naming (e.g., Author + Year format)
- Keep special characters (accents, math) in the ``title`` field escaped
  as BibTeX expects
- If OneCite cannot classify an entry confidently, it falls back to the
  ``entry_type`` declared by the selected template — see :doc:`templates`

Next Steps
----------

- Learn :doc:`templates` to customise which fields are collected
- See :doc:`quick_start` for basic usage examples
- Check :doc:`advanced_usage` for complex scenarios
