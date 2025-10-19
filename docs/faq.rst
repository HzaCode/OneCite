Frequently Asked Questions (FAQ)
================================

General Questions
-----------------

What is OneCite?
~~~~~~~~~~~~~~~~

OneCite is a universal citation and academic reference toolkit that helps you manage bibliographic data. It automates the process of converting various reference formats (DOI, titles, arXiv IDs, etc.) into clean, properly formatted citations in BibTeX, APA, or MLA formats.

How much does OneCite cost?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite is completely **free and open-source**. It's licensed under the MIT License.

What do I need to use OneCite?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need:

- Python 3.7 or higher
- pip (Python package manager)
- An internet connection (for data source access)

That's it! Just run ``pip install onecite`` and you're ready to go.

Installation Questions
----------------------

Can I use OneCite on Windows?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! OneCite works on Windows, macOS, and Linux. Simply follow the installation instructions for your system.

I'm getting a permission error when installing. What should I do?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
- **Direct identifiers** - DOI, arXiv ID, PMID, ISBN, GitHub URLs, or plain text queries

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

Use interactive mode to manually select the correct match::

    onecite process references.txt --interactive

When multiple matches are found, you'll be prompted to select the correct one.

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

OneCite integrates with:

- CrossRef (DOI metadata)
- Semantic Scholar (AI-powered search)
- OpenAlex (academic graph)
- PubMed (biomedical literature)
- DBLP (computer science)
- arXiv (preprints)
- DataCite (datasets)
- Zenodo (open research)
- Google Books (book metadata)

Which data source is best for my field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**For Biomedical Research:**
- Use PMID when available
- OneCite will prioritize PubMed for medical terms

**For Computer Science:**
- Use arXiv ID for preprints
- Use DOI from DBLP when available
- OneCite will prioritize CS-related sources

**For General Academic Work:**
- Use DOI (most comprehensive)
- Fall back to title + author for identification

Do I need API keys?
~~~~~~~~~~~~~~~~~~~

No! OneCite works without any API keys or authentication. All data sources are accessed through public APIs.

Output Format Questions
-----------------------

What output formats are supported?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite supports:

- **BibTeX** - For LaTeX/Overleaf documents
- **APA** - American Psychological Association style
- **MLA** - Modern Language Association style

Can I customize the output format?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! OneCite uses YAML-based templates. See :doc:`templates` for details on creating custom formats.

How do I convert between formats?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simply re-process your references with a different format::

    # Convert to APA
    onecite process input.bib --output-format apa -o output_apa.txt
    
    # Convert back to BibTeX
    onecite process input.bib --output-format bibtex -o output_new.bib

Can I get the output as plain text instead of a file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes, when using the Python API::

    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        output_format="apa"
    )
    
    print(result['output_content'])

Python API Questions
--------------------

Can I use OneCite in my Python project?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Import and use it like any Python library::

    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        output_format="bibtex"
    )
    print(result['output_content'])

See :doc:`python_api` for detailed examples.

How do I handle errors in the API?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    from onecite import process_references, ValidationError, ParseError
    
    try:
        result = process_references(
            input_content="invalid_reference",
            output_format="bibtex"
        )
    except ValidationError as e:
        print(f"Validation error: {e}")
    except ParseError as e:
        print(f"Parse error: {e}")

Can I use callbacks for custom handling?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Use the ``interactive_callback`` parameter::

    def my_selector(candidates):
        return 0  # Always select first match
    
    result = process_references(
        input_content="ambiguous reference",
        interactive_callback=my_selector
    )

MCP Integration Questions
-------------------------

What is MCP?
~~~~~~~~~~~~

MCP (Model Context Protocol) is an open standard for connecting AI assistants with tools. It lets Claude and other AI assistants directly use OneCite.

How do I set up MCP integration?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`mcp_integration` for detailed setup instructions for Claude Desktop and Cursor.

Can I use OneCite with other AI assistants?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite is compatible with any AI assistant that supports MCP, including:

- Claude (Claude Desktop)
- Cursor Editor
- Other future MCP-compatible assistants

Troubleshooting Questions
-------------------------

OneCite keeps skipping my references. Why?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Possible reasons:

1. **Empty or malformed references** - Check input formatting
2. **Unrecognized format** - Try using more specific identifiers (DOI instead of title)
3. **Data source unavailable** - Try again later
4. **Too broad reference** - Add more details (author, year, etc.)

**Solution:** Run with verbose output to see warnings::

    onecite process references.txt  # Remove --quiet flag

I'm getting "Connection Error". What does it mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This means OneCite couldn't connect to one or more data sources. Check:

1. **Internet connection** - Ensure you're online
2. **Data source status** - Some services may be temporarily down
3. **Firewall/Proxy** - Corporate proxies may block external APIs

Try again later or contact support if the issue persists.

Why are my references incomplete?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite retrieves what's available in the data sources. Some references may have limited metadata. To improve results:

1. Use more specific identifiers (DOI vs. title)
2. Add more context (author names, year)
3. Check if the paper exists in multiple data sources

Can I use OneCite offline?
~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite requires internet access to query academic databases. However, once you've processed references, the output can be used offline.

Performance and Limitations
---------------------------

How many references can I process at once?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneCite can handle large batches. For optimal performance:

- Up to 100 references: Use normal mode
- 100+ references: Use ``--quiet`` mode for faster processing

For very large batches (1000+), split into chunks::

    split -l 100 large_file.txt chunk_
    for chunk in chunk_*; do
        onecite process "$chunk" -o "${chunk}.bib" --quiet
    done

How long does processing take?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Typically:

- Single reference: 1-3 seconds
- 10 references: 10-30 seconds
- 100 references: 2-5 minutes

Times vary depending on data source responsiveness and network speed.

Is there a rate limit?
~~~~~~~~~~~~~~~~~~~~~~

OneCite respects rate limits of data sources. If you hit a rate limit:

1. The tool will wait and retry
2. Or skip that reference and continue
3. You can retry later

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
~~~~~~~~~~~~~~~~~~~~~~~

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
- Check :doc:`mcp_integration` for AI assistant integration
