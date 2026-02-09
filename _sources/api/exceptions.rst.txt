Exceptions Reference
====================

Overview
--------

OneCite provides a hierarchy of custom exceptions for different error scenarios. All exceptions inherit from ``OneCiteError``.

Exception Hierarchy
~~~~~~~~~~~~~~~~~~~

::

    Exception
    └── OneCiteError
        ├── ValidationError
        ├── ParseError
        └── ResolverError

OneCiteError
------------

Base exception for all OneCite errors.

**Inheritance:** ``Exception``

**Usage:**

.. code-block:: python

    from onecite import OneCiteError
    
    try:
        # OneCite operation
        pass
    except OneCiteError as e:
        print(f"OneCite error occurred: {e}")

ValidationError
---------------

Raised when entry validation fails.

**Inheritance:** ``OneCiteError``

**Common Causes:**

- Empty or null input
- Missing required fields
- Invalid data format
- Malformed identifiers

**Example:**

.. code-block:: python

    from onecite import process_references, ValidationError
    
    try:
        result = process_references(
            input_content="",  # Empty input
            input_type="txt"
        )
    except ValidationError as e:
        print(f"Validation error: {e}")

**Handling:**

.. code-block:: python

    try:
        result = process_references(reference)
    except ValidationError:
        print("Invalid reference format")
        # Provide user feedback or skip this entry
        continue

ParseError
----------

Raised when parsing input fails.

**Inheritance:** ``OneCiteError``

**Common Causes:**

- Invalid BibTeX syntax
- Unrecognized file format
- Corrupted data
- Incompatible encoding

**Example:**

.. code-block:: python

    from onecite import process_references, ParseError
    
    try:
        result = process_references(
            input_content="@article{broken syntax",
            input_type="bib"
        )
    except ParseError as e:
        print(f"Parse error: {e}")

**Handling:**

.. code-block:: python

    try:
        result = process_references(content, input_type="bib")
    except ParseError:
        print("Failed to parse BibTeX file")
        print("Ensure the file is valid BibTeX format")

ResolverError
-------------

Raised when data source resolution fails.

**Inheritance:** ``OneCiteError``

**Common Causes:**

- Network connectivity issues
- Data source unavailable
- API rate limiting
- Invalid identifier
- No matches found

**Example:**

.. code-block:: python

    from onecite import process_references, ResolverError
    
    try:
        result = process_references(
            input_content="10.invalid/doi",
            input_type="txt"
        )
    except ResolverError as e:
        print(f"Resolver error: {e}")

**Handling:**

.. code-block:: python

    try:
        result = process_references(reference)
    except ResolverError:
        print("Could not find the reference in data sources")
        print("Check your internet connection or try again later")

Error Handling
-----------------------------

Handling All Exceptions
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from onecite import (
        process_references,
        OneCiteError,
        ValidationError,
        ParseError,
        ResolverError
    )
    
    def process_safely(content, input_type="txt"):
        try:
            result = process_references(
                input_content=content,
                input_type=input_type
            )
            return result
        except ValidationError as e:
            print(f"❌ Validation failed: {e}")
            return None
        except ParseError as e:
            print(f"❌ Parse failed: {e}")
            return None
        except ResolverError as e:
            print(f"❌ Resolver failed: {e}")
            return None
        except OneCiteError as e:
            print(f"❌ Unexpected error: {e}")
            return None

Batch Processing with Error Recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from onecite import process_references, OneCiteError
    
    references = [
        "10.1038/nature14539",
        "invalid/doi",
        "Vaswani et al., 2017"
    ]
    
    results = []
    errors = []
    
    for ref in references:
        try:
            result = process_references(ref)
            results.append(result)
        except OneCiteError as e:
            errors.append({
                'reference': ref,
                'error': str(e)
            })
    
    print(f"Successfully processed: {len(results)}")
    print(f"Failed: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err['reference']}: {err['error']}")

Best Practices
--------------

1. **Be Specific** - Catch specific exceptions rather than generic Exception
2. **Log Errors** - Record error details for debugging
3. **Provide Feedback** - Give users clear feedback on what went wrong
4. **Retry on Resolver Errors** - Network issues may be temporary
5. **Validate Input** - Pre-validate input to catch ValidationErrors early

.. code-block:: python

    import logging
    from onecite import process_references, OneCiteError
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def process_with_logging(reference):
        try:
            result = process_references(reference)
            logger.info(f"Successfully processed: {reference}")
            return result
        except OneCiteError as e:
            logger.error(f"Error processing {reference}: {e}")
            raise

Next Steps
----------

- See :doc:`../api/core` for core API reference
- Check :doc:`../python_api` for usage examples
- Review :doc:`../faq` for error handling patterns
