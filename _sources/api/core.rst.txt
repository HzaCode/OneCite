Core API Reference
===================

Main Functions
--------------

process_references()
~~~~~~~~~~~~~~~~~~~~

The primary function for processing citations.

**Signature:**

.. code-block:: python

    def process_references(
        input_content: str,
        input_type: str,
        template_name: str,
        output_format: str,
        interactive_callback: Callable[[List[Dict]], int],
        use_google_scholar: bool = False,
    ) -> Dict[str, Any]

**Parameters:**

- ``input_content`` (str): The reference content to process
- ``input_type`` (str): Type of input - ``"txt"`` or ``"bib"`` (required)
- ``template_name`` (str): Template name to use (e.g., ``"journal_article_full"``) (required)
- ``output_format`` (str): Output format - currently only ``"bibtex"`` is supported (required)
- ``interactive_callback`` (Callable): Function to handle ambiguous matches. Takes a list of candidate dicts and returns the selected index (0-based), or -1 to skip (required)
- ``use_google_scholar`` (bool): Enable Google Scholar as an additional data source. Requires the optional ``scholarly`` package. Default is ``False``.

**Returns:**

A dictionary with keys:

- ``results`` (List[str]): List of formatted citation strings
- ``report`` (dict): Processing report containing:
  
  - ``total`` (int): Total number of entries processed
  - ``succeeded`` (int): Number of successfully processed entries
  - ``failed_entries`` (List[Dict]): List of failed entries with error details

**Example:**

.. code-block:: python

    from onecite import process_references
    
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0  # Auto-select first match
    )
    
    # Access results
    for citation in result['results']:
        print(citation)
    
    # Check report
    print(f"Succeeded: {result['report']['succeeded']}/{result['report']['total']}")

Data Classes
------------

RawEntry
~~~~~~~~

A TypedDict representing an unprocessed reference entry (Stage 1).

**Type Definition:**

.. code-block:: python

    class RawEntry(TypedDict, total=False):
        id: int
        raw_text: str
        doi: Optional[str]
        url: Optional[str]
        query_string: Optional[str]
        original_entry: Optional[Dict[str, Any]]

**Attributes:**

- ``id`` (int): Entry identifier
- ``raw_text`` (str): The raw reference text
- ``doi`` (str, optional): Digital Object Identifier if detected
- ``url`` (str, optional): URL if detected
- ``query_string`` (str, optional): Search query string
- ``original_entry`` (dict, optional): Preserved original BibTeX entry fields

IdentifiedEntry
~~~~~~~~~~~~~~~

A TypedDict representing an entry after identification from data sources (Stage 2).

**Type Definition:**

.. code-block:: python

    class IdentifiedEntry(TypedDict, total=False):
        id: int
        raw_text: str
        doi: Optional[str]
        arxiv_id: Optional[str]
        url: Optional[str]
        metadata: Optional[Dict[str, Any]]
        status: str

**Attributes:**

- ``id`` (int): Entry identifier
- ``raw_text`` (str): Original raw text
- ``doi`` (str, optional): Digital Object Identifier
- ``arxiv_id`` (str, optional): arXiv identifier
- ``url`` (str, optional): Conference or other URL
- ``metadata`` (dict, optional): Additional metadata from various sources
- ``status`` (str): Status - 'identified' or 'identification_failed'

CompletedEntry
~~~~~~~~~~~~~~~

A TypedDict representing a fully processed entry with all metadata (Stage 3).

**Type Definition:**

.. code-block:: python

    class CompletedEntry(TypedDict, total=False):
        id: int
        doi: str
        status: str
        bib_key: str
        bib_data: Dict[str, Any]

**Attributes:**

- ``id`` (int): Entry identifier
- ``doi`` (str): Digital Object Identifier
- ``status`` (str): Status - 'completed' or 'enrichment_failed'
- ``bib_key`` (str): BibTeX citation key (e.g., "LeCun2015Deep")
- ``bib_data`` (dict): Complete bibliographic data with all fields

CompletedEntry is a TypedDict. Use ``FormatterModule`` from ``pipeline.py`` to convert entries to different output formats.

Classes
-------

TemplateLoader
~~~~~~~~~~~~~~

Manages citation templates by loading YAML template files.

**Constructor:**

.. code-block:: python

    TemplateLoader(templates_dir: Optional[str] = None)

**Parameters:**

- ``templates_dir`` (str, optional): Custom template directory path. If None, uses the built-in ``onecite/templates/`` directory.

**Methods:**

- ``load_template(template_name: str) -> Dict[str, Any]``: Load a YAML template by name. Returns the template dictionary or a default template if not found.

**Example:**

.. code-block:: python

    from onecite import TemplateLoader
    
    # Use default templates directory
    loader = TemplateLoader()
    template = loader.load_template("journal_article_full")
    print(template['name'])
    
    # Use custom templates directory
    custom_loader = TemplateLoader(templates_dir="/path/to/templates")
    custom_template = custom_loader.load_template("my_custom_template")

PipelineController
~~~~~~~~~~~~~~~~~~~

Manages the 4-stage processing pipeline (Parse → Identify → Enrich → Format).

**Constructor:**

.. code-block:: python

    PipelineController(use_google_scholar: bool = False)

**Parameters:**

- ``use_google_scholar`` (bool): Whether to enable Google Scholar as a data source. Default is False.

**Methods:**

- ``process(input_content: str, input_type: str, template_name: str, output_format: str, interactive_callback: Callable) -> Dict[str, Any]``: Execute the complete 4-stage processing pipeline

For typical usage, ``process_references()`` is simpler. PipelineController exposes a lower-level API for advanced use cases.

**Example:**

.. code-block:: python

    from onecite import PipelineController
    
    controller = PipelineController()
    result = controller.process(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    print(result['results'])

Exceptions
----------

All exceptions inherit from ``OneCiteError``.

OneCiteError
~~~~~~~~~~~~

Base exception for all OneCite errors.

ValidationError
~~~~~~~~~~~~~~~

Raised when entry validation fails.

.. code-block:: python

    try:
        result = process_references("")
    except ValidationError as e:
        print(f"Validation failed: {e}")

ParseError
~~~~~~~~~~

Raised when parsing input fails.

.. code-block:: python

    try:
        result = process_references("invalid input", input_type="bib")
    except ParseError as e:
        print(f"Parse failed: {e}")

ResolverError
~~~~~~~~~~~~~

Raised when data source resolution fails.

.. code-block:: python

    try:
        result = process_references("nonexistent doi")
    except ResolverError as e:
        print(f"Resolver failed: {e}")

Advanced Usage
--------------

Custom Data Processing
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from onecite import process_references
    
    # For most use cases, use process_references directly
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    print('\n\n'.join(result['results']))
    
    # Access the processing report
    report = result['report']
    print(f"Total: {report['total']}, Succeeded: {report['succeeded']}")

Working with Templates
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from onecite import TemplateLoader, process_references
    
    # Load a template to inspect it
    loader = TemplateLoader()
    template = loader.load_template("journal_article_full")
    print(f"Template name: {template['name']}")
    print(f"Entry type: {template['entry_type']}")
    
    # To use a custom template, place it in onecite/templates/ directory
    # then reference it by name
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="your_custom_template",  # without .yaml extension
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )

Next Steps
----------

- See :doc:`../python_api` for usage examples
- Check :doc:`../advanced_usage` for complex scenarios
- Review :doc:`../templates` for custom formatting
