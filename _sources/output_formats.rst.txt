Output Formats
==============

OneCite writes **BibTeX** (the default) and **CSL-JSON**. Earlier versions
also advertised APA and MLA output, but those renderers produced
inconsistent results and have been removed (see issues #31 and #32). The
CLI rejects any ``--output-format`` other than ``bibtex`` or ``csl-json``.

If you need styled output (APA, MLA, …), emit CSL-JSON and pipe it through
a dedicated renderer such as `pandoc <https://pandoc.org/>`_ or
`citeproc-py <https://github.com/brechtm/citeproc-py>`_ — these consume
CSL-JSON directly.

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
      abstract = "Deep learning allows computational models that are composed of multiple processing layers to learn representations of data with multiple levels of abstraction...",
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
        output_format="bibtex"
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

CSL-JSON Format
---------------

CSL-JSON is the interchange format consumed by pandoc, Quarto, citeproc,
and reference-manager imports. The CLI emits one valid JSON array::

    onecite process references.txt --output-format csl-json -o references.json

::

    [
      {
        "id": "LeCun2015Deep",
        "type": "article-journal",
        "title": "Deep learning",
        "author": [
          {"family": "LeCun", "given": "Yann"},
          {"family": "Bengio", "given": "Yoshua"},
          {"family": "Hinton", "given": "Geoffrey"}
        ],
        "container-title": "Nature",
        "issued": {"date-parts": [[2015]]},
        "volume": "521",
        "issue": "7553",
        "page": "436-444",
        "DOI": "10.1038/nature14539"
      }
    ]

Values are plain Unicode (no LaTeX escapes). Author names are structured
``family``/``given`` pairs when the source metadata provides them;
organization names stay as ``literal`` names rather than being guessed
apart. In the Python API, ``output_format="csl-json"`` returns one CSL
item (a JSON object string) per entry in ``results``.

Use CSL-JSON with pandoc::

    pandoc paper.md --citeproc --bibliography references.json -o paper.pdf

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
