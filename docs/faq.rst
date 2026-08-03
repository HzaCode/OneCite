Frequently Asked Questions (FAQ)
================================

General Questions
-----------------

What is OneCite?
~~~~~~~~~~~~~~~~

OneCite is a citation-normalization toolkit. It routes supported identifiers to
metadata services and emits BibTeX or CSL-JSON. Ordinary title/author text is
searched with ``suggest`` and remains a candidate for review rather than being
silently accepted by ``process``.

How much does OneCite cost?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite is completely **free and open-source**. It's licensed under the MIT License.

What do I need to use OneCite?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need:

- Python 3.10 or higher
- pip (Python package manager)
- Network access for ordinary live ``process`` and ``suggest`` lookups

After installation, local commands such as ``templates``, ``doctor``, and the
default offline ``benchmark`` do not require provider access. See
:doc:`external_services` for the live/offline boundary.

Installation Questions
----------------------

Can I use OneCite on Windows?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! OneCite works on Windows, macOS, and Linux. Simply follow the installation instructions for your system.

I'm getting a permission error when installing. What should I do?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Try one of these solutions:

1. Use a virtual environment (recommended)::

    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install onecite

2. Or use the ``--user`` flag::

    pip install --user onecite

Can I install OneCite from source?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Clone the repository and install in development mode::

    git clone https://github.com/HzaCode/OneCite.git
    cd OneCite
    pip install -e ".[dev]"

Usage Questions
---------------

What file formats can I input?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite accepts:

- **Plain text** (`.txt`) - One reference per line or separated by blank lines
- **BibTeX** (`.bib`) - Standard BibTeX format
- **Direct identifiers** - DOI, arXiv ID, PMID, ISBN, GitHub URLs, Zenodo DOI, or DataCite DOI
- **Candidate suggestions** - Use ``onecite suggest`` for plain-text title queries

Can I use OneCite with Overleaf?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Here's how:

1. Generate your bibliography locally::

    onecite process references.txt -o mybib.bib

2. Upload ``mybib.bib`` to your Overleaf project
3. In your LaTeX file::

    \bibliography{mybib}
    \bibliographystyle{plain}

4. Compile and you're done!

How do I handle ambiguous references?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``onecite process`` does not fuzzy-match an ordinary ambiguous plain-text
reference. Use ``onecite suggest`` to get candidate matches and review them
yourself::

    onecite suggest "deep learning hinton 2015"

Candidates are returned for human review, not promoted to source-resolved
bibliography output. Explicitly labelled thesis/dissertation citations are a
separate ``process`` route; see :doc:`external_services`.

Can I process multiple files at once?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Use a shell loop::

    # On macOS/Linux
    for file in *.txt; do
        onecite process "$file" -o "${file%.txt}.bib"
    done

    # On Windows PowerShell
    Get-ChildItem *.txt | ForEach-Object {
        onecite process $_.FullName -o "$($_.BaseName).bib"
    }

Data Source Questions
---------------------

What data sources does OneCite use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite has input-dependent routes for:

- CrossRef (DOI metadata)
- Semantic Scholar (keyword search)
- PubMed (biomedical literature)
- arXiv (preprints)
- DataCite (datasets)
- Zenodo (open research)
- Google Books (book metadata)
- OpenAIRE / BASE (theses & grey literature)
- GitHub (software repositories)
- Google Scholar (optional scraping-based ``suggest`` fallback, off by default)

Not every source is queried for every input. ``process`` routes identifiers;
``suggest`` always consults Crossref, Semantic Scholar, and arXiv when it has a
usable query and conditionally consults the other sources. The precise triggers
and data sent are documented in :doc:`external_services`.

Which data source is best for my field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**For Biomedical Research:**
- Use PMID when available
- ``suggest`` additionally queries PubMed when it detects strong medical cues

**For Computer Science:**
- Use arXiv ID for preprints
- Use DOI when available
- CrossRef and Semantic Scholar cover most CS venues

**For General Academic Work:**
- Use DOI (most reliable)
- Use title + author with ``suggest`` for candidates; review one, then resolve its trusted identifier with ``process``

Do I need API keys?
~~~~~~~~~~~~~~~~~~~

The currently implemented default routes do not require users to configure API
keys. That does not mean every route is a public API: the optional Google
Scholar fallback uses the ``scholarly`` scraper, and it can be blocked or
challenged by a CAPTCHA. Other unauthenticated services, including GitHub and
Semantic Scholar, can throttle requests. Crossref receives OneCite's package
contact in its request identification. Provider access rules can change; see
:doc:`external_services`.

Output Format Questions
-----------------------

What output formats are supported?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite writes **BibTeX** and **CSL-JSON**. Use
``--output-format csl-json`` for a JSON array compatible with tools such as
pandoc, Quarto, and citeproc. Earlier versions also offered direct APA and MLA
renderers, but those were removed (see issues #31 and #32) because they
produced inconsistent output.

For APA or MLA, post-process BibTeX or CSL-JSON with a dedicated tool such as
`pandoc <https://pandoc.org/>`_ or
`citeproc-py <https://github.com/brechtm/citeproc-py>`_.

Can I customize which fields end up in the BibTeX output?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not as a strict include/exclude filter. Templates declare expected fields and
provide the fallback entry type when classification is ambiguous, but the
current enricher can emit other fields returned by the selected source and
does not run broad completion merely because a template lists a source. See
:doc:`templates` for details.

How do I re-run OneCite on an existing BibTeX file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    onecite process input.bib --input-type bib -o output_new.bib

Can I get the output as plain text instead of a file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes, when using the Python API::

    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
    )
    
    print('\n\n'.join(result['results']))

Python API Questions
--------------------

Can I use OneCite in my Python project?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Import and use it like any Python library::

    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
    )
    print('\n\n'.join(result['results']))

See :doc:`python_api` for detailed examples.

How do I handle errors in the API?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    from onecite import process_references, ValidationError, ParseError
    
    try:
        result = process_references(
            input_content="invalid_reference",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
        )
    except ValidationError as e:
        print(f"Validation error: {e}")
    except ParseError as e:
        print(f"Parse error: {e}")
    else:
        # Ordinary unresolved entries are returned, not raised.
        for failed in result["report"]["failed_entries"]:
            print(failed["reason"], failed["raw_text"])

Can I use callbacks to auto-select candidates?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No — ``process_references`` is strictly non-interactive and fail-closed.
The ``interactive_callback`` parameter is accepted for backward
compatibility but never invoked. For ambiguous references, get ranked
candidates with ``suggest_references``, review them, and resolve the chosen
candidate's DOI through ``process_references``::

    from onecite import suggest_references, process_references

    candidates = suggest_references("ambiguous reference title")
    # ...review candidates, pick a DOI...
    result = process_references(
        input_content="10.1234/chosen.doi",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
    )

Troubleshooting Questions
-------------------------

OneCite keeps skipping my references. Why?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Possible reasons:

1. **Empty or malformed references** - Check input formatting
2. **No strong identifier** - Use a DOI/PMID/arXiv ID/ISBN/URL when available,
   or send ordinary title text to ``suggest``
3. **Data source unavailable** - Try again later
4. **Too broad suggestion query** - Add author/year context to ``suggest``;
   adding it to ``process`` does not enable fuzzy acceptance

**Solution:** Run with verbose output to see warnings::

    onecite process references.txt  # Remove --quiet flag

I'm getting "Connection Error". What does it mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This means OneCite could not complete one or more external routes. Check:

1. **Internet connection** - Ensure you're online
2. **Data source status** - Some services may be temporarily down
3. **Firewall/Proxy** - Corporate proxies may block external APIs

For ``suggest``, inspect ``--json``: the ``sources`` list reports Crossref,
Semantic Scholar, and arXiv health for that query. Conditional sources are not
all represented there. For ``process``, inspect failure reason codes and
verbose logs. See :doc:`external_services` before retrying large jobs.

Why are my references incomplete?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite retrieves what's available in the data sources. Some references may have limited metadata. To improve results:

1. Use more specific identifiers (DOI vs. title)
2. If the input is ordinary text, search it with ``suggest`` and review the
   candidate rather than expecting ``process`` to choose a title match
3. Compare the result with the provider record; source resolution does not
   guarantee complete or correct upstream metadata

Can I use OneCite offline?
~~~~~~~~~~~~~~~~~~~~~~~~~~

Ordinary live ``process`` and ``suggest`` lookups require access to the
applicable external services. ``onecite benchmark`` is fixture-backed and
offline by default; ``onecite doctor``, ``onecite templates``, and
``onecite --version`` are also local after installation. ``benchmark --live``
opts back into external requests. Passing the offline benchmark or doctor does
not prove that live services are reachable. Previously written output can be
used offline.

Performance and Limitations
---------------------------

How many references can I process at once?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite processes entries sequentially. ``--quiet`` changes logging, not
network speed. For long jobs, split inputs into recoverable chunks and retain
JSON reports; choose a chunk size that is appropriate for the routes and
provider limits involved::

    split -l 100 large_file.txt chunk_
    for chunk in chunk_*; do
        onecite process "$chunk" -o "${chunk}.bib" --quiet
    done

How long does processing take?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is no stable per-reference duration. Runtime depends on identifier type,
fallbacks, timeouts, provider latency, throttling, and whether optional Google
Scholar scraping is enabled. Measure with representative input in your own
environment; do not use the offline benchmark as a latency estimate for live
services.

Is there a rate limit?
~~~~~~~~~~~~~~~~~~~~~~

Each external provider defines and can change its own limits. OneCite retries
some specific ``suggest`` routes with short backoff, while other routes fail or
return no metadata without a common global retry policy. ``suggest --json``
uses ``rate_limited`` for Semantic Scholar or arXiv when that condition remains
detectable after their retry path; other provider failures may appear as
``error`` or only in logs. Do not assume every ``429`` is retried or surfaced
identically. Reduce request volume and follow the provider's current guidance
before retrying.

Contributing & Support
----------------------

How can I contribute to OneCite?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`contributing` for guidelines on:

- Reporting bugs
- Suggesting features
- Submitting pull requests
- Improving documentation

Where can I report bugs?
~~~~~~~~~~~~~~~~~~~~~~~~

Report issues on GitHub: https://github.com/HzaCode/OneCite/issues

Can I suggest new features?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Open a feature request on GitHub or discuss in the discussions section.

Where do I get help?
~~~~~~~~~~~~~~~~~~~~

- Check the documentation: :doc:`quick_start`
- Search existing issues on GitHub
- Ask in GitHub discussions
- Contact the team for specific problems

Next Steps
----------

- See :doc:`quick_start` to get started
- Learn :doc:`python_api` for programmatic access
- Explore :doc:`templates` for custom formats
