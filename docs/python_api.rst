Python API Reference
====================

This guide covers using OneCite as a Python library in your own code.

Basic Usage
-----------

Simple Citation Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    from onecite import process_references
    
    # Process a simple reference
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: -1
    )
    
    # Print results
    for citation in result['results']:
        print(citation)

The Result Dictionary
~~~~~~~~~~~~~~~~~~~~~

The ``process_references`` function returns a dictionary containing:

- ``results`` (List[str]): List of formatted citation strings
- ``report`` (dict): Processing report with keys:
  
  - ``total`` (int): Total number of entries processed
  - ``succeeded`` (int): Number of successfully processed entries
  - ``failed_entries`` (List[Dict]): List of failed entries with error details

::

    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    print(f"Total: {result['report']['total']}")
    print(f"Succeeded: {result['report']['succeeded']}")
    print(f"Failed: {len(result['report']['failed_entries'])}")

Processing Different Input Formats
-----------------------------------

Plain Text Input
~~~~~~~~~~~~~~~~

::

    from onecite import process_references
    
    txt_content = """
    10.1038/nature14539
    
    arXiv:1706.03762
    
    ISBN:9780262035613
    """
    
    result = process_references(
        input_content=txt_content,
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    # Access results
    print('\n\n'.join(result['results']))

BibTeX Input
~~~~~~~~~~~~

::

    from onecite import process_references
    
    bibtex_content = """
    @article{LeCun2015,
        title = {Deep Learning},
        author = {LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
        journal = {Nature},
        year = {2015}
    }
    """
    
    result = process_references(
        input_content=bibtex_content,
        input_type="bib",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    print('\n\n'.join(result['results']))

Output Formats
--------------

OneCite currently supports BibTeX output only::

    # BibTeX format — the only supported output format
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )

Passing any other value (such as ``"apa"`` or ``"mla"``) raises
``FormatError``; that support was removed in favour of dedicated
BibTeX-to-APA/MLA tools like pandoc or citeproc-py.

Interactive Selection with Callbacks
-------------------------------------

For plain-text title searches, use the suggestion API instead of resolving
directly to BibTeX:

::

    from onecite import suggest_references
    
    result = suggest_references(
        input_content="Deep learning Hinton",
        input_type="txt",
        limit=5,
    )
    
    print('\n\n'.join(result['results']))

Custom Callback Logic
~~~~~~~~~~~~~~~~~~~~~

::

    def pick_most_complete(candidates):
        """Pick the candidate with the most filled-in fields."""
        best_idx = 0
        best_score = 0
        
        for idx, candidate in enumerate(candidates):
            # Score based on number of fields
            score = sum(1 for v in candidate.values() if v)
            if score > best_score:
                best_score = score
                best_idx = idx
        
        return best_idx
    
    result = process_references(
        input_content="Deep learning nature 2015",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=pick_most_complete
    )
    
    print('\n\n'.join(result['results']))

Advanced Data Structures
------------------------

OneCite defines three TypedDict classes representing different stages of the processing pipeline:

RawEntry
~~~~~~~~

A TypedDict representing an unprocessed reference entry (Stage 1):

::

    from onecite import RawEntry
    from typing import Dict, Any, Optional
    
    # RawEntry is a TypedDict with these fields:
    entry: RawEntry = {
        'id': 1,
        'raw_text': "10.1038/nature14539",
        'doi': "10.1038/nature14539",
        'url': None,
        'query_string': None,
        'original_entry': None
    }

IdentifiedEntry
~~~~~~~~~~~~~~~

A TypedDict representing an entry after identification from data sources (Stage 2):

::

    from onecite import IdentifiedEntry
    
    # IdentifiedEntry includes fields like:
    # id, raw_text, doi, arxiv_id, url, metadata, status

CompletedEntry
~~~~~~~~~~~~~~~

A TypedDict representing a fully processed entry with all metadata (Stage 3):

::

    from onecite import CompletedEntry
    
    # CompletedEntry includes fields like:
    # id, doi, status, bib_key, bib_data

These are TypedDict classes used internally by the pipeline. For typical usage, call ``process_references()`` directly.

Working with Templates
----------------------

Load and inspect templates::

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

Using the Pipeline Controller
------------------------------

For advanced use cases requiring more control over the processing pipeline:

::

    from onecite import PipelineController
    
    # Create controller (optionally enable Google Scholar)
    controller = PipelineController(use_google_scholar=False)
    
    # Process with full control
    result = controller.process(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    print('\n\n'.join(result['results']))

For typical usage, ``process_references()`` is simpler and covers the same functionality.

Error Handling
--------------

Handling Exceptions
~~~~~~~~~~~~~~~~~~~

::

    from onecite import process_references, ValidationError, ParseError
    
    try:
        result = process_references(
            input_content="invalid_reference",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda candidates: 0
        )
    except ValidationError as e:
        print(f"Validation error: {e}")
    except ParseError as e:
        print(f"Parse error: {e}")
    except Exception as e:
        print(f"Processing error: {e}")

Processing Files
----------------

Reading from File
~~~~~~~~~~~~~~~~~

::

    from onecite import process_references
    
    # Read from file
    with open("references.txt", "r", encoding="utf-8") as f:
        content = f.read()
    
    result = process_references(
        input_content=content,
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    # Write to file
    output_content = '\n\n'.join(result['results'])
    with open("output.bib", "w", encoding="utf-8") as f:
        f.write(output_content)

Complete Example
----------------

::

    from onecite import process_references
    
    # Read references
    with open("my_references.txt", "r", encoding="utf-8") as f:
        references = f.read()
    
    # Process with BibTeX format
    result = process_references(
        input_content=references,
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: -1
    )
    
    # Check results
    report = result['report']
    print(f"Total entries: {report['total']}")
    print(f"Successfully processed: {report['succeeded']}")
    print(f"Failed: {len(report['failed_entries'])}")
    
    if report['failed_entries']:
        print("\nFailed entries:")
        for failed in report['failed_entries']:
            print(f"  - Entry {failed['id']}: {failed.get('error', 'Unknown error')}")
    
    # Save output
    output_content = '\n\n'.join(result['results'])
    with open("formatted_refs.txt", "w", encoding="utf-8") as f:
        f.write(output_content)
    
    print("\nDone!")

API Reference
-------------

See :doc:`api/core` for the complete API documentation.

Next Steps
----------

- Explore :doc:`templates` for custom formatting
- Check :doc:`faq` for common questions
