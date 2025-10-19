Output Formats
==============

OneCite supports multiple citation formats. This guide explains each format and how to use them.

Supported Formats
-----------------

OneCite currently supports three primary citation formats:

1. **BibTeX** - for LaTeX/Overleaf documents
2. **APA** - American Psychological Association style
3. **MLA** - Modern Language Association style

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

    # Command line
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

1. Save references to a `.bib` file using OneCite
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

Common entry types supported:

- ``@article`` - Journal article
- ``@inproceedings`` - Conference paper
- ``@book`` - Book
- ``@phdthesis`` - PhD thesis
- ``@mastersthesis`` - Master's thesis
- ``@misc`` - Miscellaneous
- ``@software`` - Software
- ``@dataset`` - Dataset

APA Format
----------

APA (American Psychological Association) format is widely used in social sciences and psychology.

Format Specification
~~~~~~~~~~~~~~~~~~~~

**Basic format:**

::

    Author(s) (Year). Title of work. Source.

**Journal article example:**

::

    LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.

**Book example:**

::

    Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep learning. MIT Press.

**Thesis example:**

::

    Smith, J. (2020). Neural architecture search (Doctoral dissertation, Stanford University).

Using APA Format
~~~~~~~~~~~~~~~~

::

    # Command line
    onecite process references.txt -o output.txt --output-format apa
    
    # Python API
    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="apa",
        interactive_callback=lambda candidates: 0
    )
    
    for citation in result['results']:
        print(citation)

APA Formatting Rules
~~~~~~~~~~~~~~~~~~~~

1. **Authors** - Last name and initials
2. **Year** - In parentheses
3. **Title** - Sentence case (only first word capitalized)
4. **Source** - Journal name in italics
5. **Punctuation** - Periods after each major section

MLA Format
----------

MLA (Modern Language Association) format is commonly used in humanities and literature.

Format Specification
~~~~~~~~~~~~~~~~~~~~

**Basic format:**

::

    Author(s). "Title of Work." Source, Year.

**Journal article example:**

::

    LeCun, Yann, et al. "Deep Learning." Nature, vol. 521, no. 7553, 2015, pp. 436-444.

**Book example:**

::

    Goodfellow, Ian, et al. Deep Learning. MIT Press, 2016.

**Thesis example:**

::

    Smith, John. Neural Architecture Search. Stanford University, 2020.

Using MLA Format
~~~~~~~~~~~~~~~~

::

    # Command line
    onecite process references.txt -o output.txt --output-format mla
    
    # Python API
    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="mla",
        interactive_callback=lambda candidates: 0
    )
    
    for citation in result['results']:
        print(citation)

MLA Formatting Rules
~~~~~~~~~~~~~~~~~~~~

1. **Authors** - Last name, First name
2. **Title** - In quotation marks or italics
3. **Publication Date** - At the end
4. **Page Numbers** - "pp." for multiple pages
5. **Medium** - Type of source (Print, Web, etc.)

Format Comparison
-----------------

=============  =====================================  =====================================  =====================================
Element        BibTeX                               APA                                  MLA
=============  =====================================  =====================================  =====================================
Author Format  LeCun, Yann and others              LeCun, Y., Bengio, Y., & Hinton, G. LeCun, Yann, et al.
Title Format   In "field"                          Sentence case                        In "quotes" or italics
Journal/Source journal = "Nature"                   Nature                               Nature
Year Format    year = 2015                          (2015)                               2015
Pages Format   pages = "436-444"                    521(7553), 436-444                   vol. 521, no. 7553, pp. 436-444
=============  =====================================  =====================================  =====================================

Choosing a Format
-----------------

**Use BibTeX if:**

- You're writing a LaTeX/Overleaf document
- You need integration with bibliography tools
- You want precise control over formatting

**Use APA if:**

- You're writing for social sciences, psychology, or education
- Your institution requires APA style
- You're submitting to APA-affiliated journals

**Use MLA if:**

- You're writing for humanities or literature courses
- Your institution requires MLA style
- You're submitting to MLA-affiliated publications

Converting Between Formats
---------------------------

Convert from BibTeX to APA
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    # Process the original file to APA
    onecite process input.bib --output-format apa -o output_apa.txt

Convert from APA to BibTeX
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    # Process back to BibTeX
    onecite process input_apa.txt --output-format bibtex -o output_bibtex.bib

Batch Format Conversion
~~~~~~~~~~~~~~~~~~~~~~~

::

    # Convert all .bib files to APA
    for file in *.bib; do
        onecite process "$file" --output-format apa -o "${file%.bib}_apa.txt"
    done

Tips for Different Formats
---------------------------

**BibTeX Tips:**

- Use consistent key naming (e.g., Author Year format)
- Keep special characters in title (e.g., "Deep Learning")
- Use abbreviated month names (jan, feb, mar, etc.)

**APA Tips:**

- Use "et al." after 3rd author
- Use ampersand (&) before last author
- Use title case for book titles but sentence case for article titles

**MLA Tips:**

- Use "et al." for any number of additional authors
- Use page numbers for online sources when available
- Include "Works Cited" page with proper hanging indentation

Next Steps
----------

- Learn :doc:`templates` to customize formats
- See :doc:`quick_start` for basic usage examples
- Check :doc:`advanced_usage` for complex scenarios
