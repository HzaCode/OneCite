Custom Templates
================

OneCite uses YAML-based templates to define citation metadata field requirements. This guide explains how templates work and how to create custom ones.

Template Basics
---------------

Templates define the **structure and metadata requirements** for different citation types. OneCite comes with built-in templates for:

- **journal_article_full** - Journal articles with complete metadata (includes ``abstract`` as an optional field)
- **conference_paper** - Conference proceedings papers
- **book** - Books and monographs
- **thesis** - Theses and dissertations
- **software** - Software and code repositories
- **dataset** - Research datasets

A legacy ``journal_article_with_abstract`` template is also shipped for
backwards compatibility with older configurations. Since ``journal_article_full``
now also declares ``abstract`` as an optional field, the two templates
behave equivalently for journal articles; new configurations should
prefer ``journal_article_full`` and treat ``journal_article_with_abstract``
as deprecated.

Default Templates Location
~~~~~~~~~~~~~~~~~~~~~~~~~~

Built-in templates are located in the ``src/onecite/templates/`` directory:

- ``journal_article_full.yaml``
- ``journal_article_with_abstract.yaml`` *(deprecated alias of the above)*
- ``conference_paper.yaml``
- ``book.yaml``
- ``thesis.yaml``
- ``software.yaml``
- ``dataset.yaml``

Inspecting Templates from the CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``onecite templates`` to list the bundled fallback BibTeX templates and
their required / optional fields::

    onecite templates

Use JSON output when another tool needs to inspect the same metadata::

    onecite templates --json

What Templates Actually Do
---------------------------

OneCite templates define **metadata field requirements**, not output formatting.

Output formatting (BibTeX or CSL-JSON) is implemented in the Python code, not
in the YAML templates.

Templates declare:

1. **Which fields** are required or optional for a citation type
2. **BibTeX entry type** (e.g., @article, @book, @inproceedings)
3. **Field declarations** for template validation (the template lists which fields are expected, but broad template-driven field completion from external scrapers has been removed; only DOI-only abstract back-fill remains in `_complete_fields`)

Templates DO NOT control:

- Serialized output format or style (BibTeX/CSL-JSON formatting)
- Field ordering in the output
- Punctuation or capitalization rules

Template Structure
------------------

A template YAML file has three main parts:

1. **name** - Template identifier
2. **entry_type** - BibTeX entry type (e.g., @article, @book)
3. **fields** - List of field definitions

Example: Journal Article Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's the actual ``journal_article_full.yaml`` template::

    name: journal_article_full
    entry_type: "@article"
    fields:
      - name: author
        required: true
      - name: title
        required: true
      - name: journal
        required: true
      - name: year
        required: true
      - name: volume
        required: false
        source_priority: 
          - crossref_api
          - user_prompt
      - name: number
        required: false
        source_priority:
          - crossref_api
          - user_prompt
      - name: pages
        required: false
        source_priority:
          - crossref_api
          - google_scholar_scraper
      - name: publisher
        required: false
        source_priority:
          - crossref_api
          - user_prompt
      - name: doi
        required: false
        source_priority:
          - crossref_api

Field Definitions
~~~~~~~~~~~~~~~~~

Each field has:

- ``name`` - Field name (e.g., author, title, journal)
- ``required`` - Whether this field is required (true/false)
- ``source_priority`` - Ordered list of data sources (legacy field, preserved in templates for backwards compatibility)

Historical Note on source_priority
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``source_priority`` field was originally designed to drive optional field completion from multiple data sources. As of 0.1.1, broad template-driven field completion from external scrapers has been removed (see pipeline documentation). The ``source_priority`` declarations remain in templates as field metadata but no longer drive automated multi-source completion. The only remaining automated enrichment is the DOI-only abstract fallback cascade (Semantic Scholar → PubMed) for entries where the raw input contained a DOI.

Special Citation Types
~~~~~~~~~~~~~~~~~~~~~~

Some citation types are automatically detected and enriched during identification:

- **Software:** GitHub repositories via GitHub API
- **Dataset:** Zenodo/Figshare via their APIs
- **Thesis:** Via OpenAIRE/BASE APIs, with an input-derived fallback when no
  provider record is returned
- **Books:** Via Google Books API

Example Templates
-----------------

Conference Paper Template
~~~~~~~~~~~~~~~~~~~~~~~~~

``conference_paper.yaml``::

    name: conference_paper
    entry_type: "@inproceedings"
    fields:
      - name: author
        required: true
      - name: title
        required: true
      - name: booktitle
        required: true
      - name: year
        required: true
      - name: pages
        required: false
        source_priority:
          - crossref_api
          - google_scholar_scraper
      - name: organization
        required: false
        source_priority:
          - crossref_api
          - user_prompt
      - name: publisher
        required: false
        source_priority:
          - crossref_api
          - user_prompt
      - name: doi
        required: false
        source_priority:
          - crossref_api

Book Template
~~~~~~~~~~~~~

``book.yaml``::

    name: book
    entry_type: "@book"
    fields:
      - name: author
        required: true
      - name: title
        required: true
      - name: publisher
        required: true
      - name: year
        required: true
      - name: edition
        required: false
        source_priority:
          - crossref_api
          - user_prompt
      - name: isbn
        required: false
        source_priority:
          - crossref_api
      - name: address
        required: false
        source_priority:
          - crossref_api
          - user_prompt
      - name: pages
        required: false
        source_priority:
          - crossref_api
      - name: doi
        required: false
        source_priority:
          - crossref_api

Creating Custom Templates
--------------------------

To create a custom template:

1. Create a new YAML file in ``src/onecite/templates/``
2. Define the name, entry_type, and fields
3. Specify required fields and source priorities
4. Use the template by its name (without .yaml extension)

Example: Minimal Article Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``minimal_article.yaml``::

    name: minimal_article
    entry_type: "@article"
    fields:
      - name: author
        required: true
      - name: title
        required: true
      - name: year
        required: true
      - name: doi
        required: false
        source_priority:
          - crossref_api

Using Custom Templates
~~~~~~~~~~~~~~~~~~~~~~~

Command line::

    onecite process references.txt --template minimal_article -o output.bib

Python API::

    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="minimal_article",  # Your custom template
        output_format="bibtex"
    )
    
    print('\n\n'.join(result['results']))

Inspecting Templates
--------------------

You can load and inspect templates programmatically::

    from onecite import TemplateLoader
    
    loader = TemplateLoader()
    
    # Load a specific template
    template = loader.load_template("journal_article_full")
    print(f"Template name: {template['name']}")
    print(f"Entry type: {template['entry_type']}")
    print(f"Fields: {[f['name'] for f in template['fields']]}")
    
    # Use a custom templates directory
    custom_loader = TemplateLoader(templates_dir="/path/to/templates")
    custom_template = custom_loader.load_template("my_template")

Output Format Control
---------------------

OneCite writes BibTeX or CSL-JSON. The template does not select between them;
use ``--output-format``::

    onecite process refs.txt --output-format bibtex
    onecite process refs.txt --output-format csl-json -o refs.json

The template supplies field declarations and a fallback entry type. It does
not control the serialized output format or trigger broad multi-source field
completion.

Best Practices
--------------

1. **Start Simple** - Begin with a basic template and add fields when necessary
2. **Test with Real Data** - Verify your template works with actual references
3. **Prioritize Reliable Sources** - List most reliable data sources first in source_priority
4. **Mark Critical Fields as Required** - Only mark essential fields as required
5. **Document Your Templates** - Add comments explaining the purpose
6. **Validate YAML Syntax** - Ensure proper YAML formatting

Common Field Names
------------------

Standard BibTeX field names:

- ``author`` - Author names
- ``title`` - Work title
- ``journal`` - Journal name (articles)
- ``booktitle`` - Book/conference title (proceedings)
- ``year`` - Publication year
- ``volume`` - Volume number
- ``number`` - Issue number
- ``pages`` - Page range
- ``publisher`` - Publisher name
- ``doi`` - Digital Object Identifier
- ``url`` - Web URL
- ``isbn`` - Book identifier
- ``issn`` - Journal identifier
- ``edition`` - Edition number
- ``address`` - Publisher location
- ``organization`` - Conference/organization name

Troubleshooting
---------------

Template Not Found
~~~~~~~~~~~~~~~~~~

If you get "template not found" error:

1. Check the template file is in ``src/onecite/templates/`` directory
2. Verify the filename matches (e.g., ``my_template.yaml``)
3. Use the template name without ``.yaml`` extension
4. Ensure YAML syntax is valid

Missing Fields in Output
~~~~~~~~~~~~~~~~~~~~~~~~

If expected fields are missing:

1. Check that the field is defined in the template
2. Verify data sources are available and accessible
3. Check that source_priority lists appropriate sources
4. Consider marking critical fields as ``required: true``

Invalid YAML Syntax
~~~~~~~~~~~~~~~~~~~~

If template loading fails:

1. Use a YAML validator to check syntax
2. Ensure proper indentation (use spaces, not tabs)
3. Check that all field names are strings
4. Verify boolean values are lowercase (true/false)

Sharing Templates
-----------------

To share custom templates:

1. Save as a ``.yaml`` file with a descriptive name
2. Include a comment at the top explaining its purpose
3. Test with various reference types
4. Share in the OneCite community or contribute to the project

Next Steps
----------

- See :doc:`quick_start` for basic usage
- Learn :doc:`python_api` for programmatic access
- Check :doc:`advanced_usage` for complex scenarios
- View the ``src/onecite/templates/`` directory for more examples
