Pipeline Processing Reference
==============================

Overview
--------

The OneCite pipeline is a 4-stage process that transforms raw references into formatted citations:

1. **Validation** - Check reference validity
2. **Identification** - Query data sources
3. **Completion** - Enrich with metadata
4. **Formatting** - Convert to output format

Pipeline Stages
===============

Stage 1: Validation
-------------------

**Purpose:** Ensure input is valid and can be processed

**Input:** Raw reference text

**Output:** Validated RawEntry object

**Process:**

1. Check for empty/null input
2. Validate format (txt or bib)
3. Detect reference type
4. Extract metadata hints

**Error Handling:**

Raises ``ValidationError`` if:

- Input is empty
- Format is unrecognized
- Data is malformed
- Required fields missing

**Example:**

::

    from onecite import RawEntry
    from onecite.pipeline import Validator
    
    raw = RawEntry(content="10.1038/nature14539")
    validator = Validator()
    
    if validator.validate(raw):
        print("Valid reference")
    else:
        print("Invalid reference")

Stage 2: Identification
-----------------------

**Purpose:** Find matching citations in data sources

**Input:** Validated RawEntry

**Output:** List of IdentifiedEntry objects

**Process:**

1. Detect identifier type (DOI, arXiv, etc.)
2. Query appropriate data source
3. Parse results
4. Rank by relevance
5. Return candidates

**Data Sources:**

- CrossRef (DOI-based)
- Semantic Scholar (keyword search)
- OpenAlex (academic graph)
- PubMed (biomedical)
- DBLP (computer science)
- arXiv (preprints)
- DataCite (datasets)
- Zenodo (open research)
- Google Books (books)

**Routing:**

OneCite automatically selects best sources:

- **Medical terms** → PubMed priority
- **CS terms** → DBLP/arXiv priority
- **DOI** → CrossRef priority
- **Mixed** → Semantic Scholar

**Example:**

::

    from onecite.pipeline import Identifier
    from onecite import RawEntry
    
    identifier = Identifier()
    raw = RawEntry(content="10.1038/nature14539")
    
    matches = identifier.identify(raw)
    for match in matches:
        print(f"{match.title} ({match.year})")

Stage 3: Completion
-------------------

**Purpose:** Enrich entries with complete metadata

**Input:** IdentifiedEntry (often incomplete)

**Output:** CompletedEntry (fully enriched)

**Process:**

1. Query additional data sources
2. Fill missing fields
3. Normalize author names
4. Verify publication details
5. Calculate completeness score

**Fields Enriched:**

- Authors
- Title
- Journal/Publisher
- Year
- Volume/Issue
- Pages
- DOI/URL
- Keywords
- Abstract

**Completeness Scoring:**

A score from 0-1 indicating data completeness:

- 0.9-1.0: Excellent (all fields present)
- 0.7-0.9: Good (most fields present)
- 0.5-0.7: Fair (core fields present)
- < 0.5: Poor (incomplete)

**Example:**

::

    from onecite.pipeline import Completer
    from onecite import IdentifiedEntry
    
    completer = Completer()
    identified = IdentifiedEntry(...)
    
    completed = completer.complete(identified)
    print(f"Completeness: {completed.completeness_score}")

Stage 4: Formatting
-------------------

**Purpose:** Convert to output format

**Input:** CompletedEntry

**Output:** Formatted string

**Supported Formats:**

- BibTeX
- APA
- MLA
- Custom (via templates)

**Process:**

1. Load template for format
2. Map fields to template variables
3. Apply formatting rules
4. Handle special characters
5. Return formatted string

**Example:**

::

    from onecite.pipeline import Formatter
    from onecite import CompletedEntry
    
    formatter = Formatter()
    completed = CompletedEntry(...)
    
    # BibTeX output
    bibtex = formatter.format(completed, "bibtex")
    
    # APA output
    apa = formatter.format(completed, "apa")

Complete Pipeline
=================

The PipelineController orchestrates all stages:

::

    from onecite import PipelineController
    
    controller = PipelineController()
    
    result = controller.process(
        entries=["10.1038/nature14539"],
        output_format="bibtex"
    )

Internal Process
~~~~~~~~~~~~~~~~

1. Validate input
2. For each entry:
   - Identify sources
   - Select best match
   - Complete entry
   - Format output
3. Aggregate results
4. Return summary

Advanced Pipeline Usage
=======================

Custom Data Processing
----------------------

::

    from onecite.pipeline import (
        Validator,
        Identifier,
        Completer,
        Formatter
    )
    from onecite import RawEntry
    
    # Create components
    validator = Validator()
    identifier = Identifier()
    completer = Completer()
    formatter = Formatter()
    
    # Manual pipeline
    raw = RawEntry(content="10.1038/nature14539")
    
    # Stage 1
    if not validator.validate(raw):
        raise ValidationError("Invalid reference")
    
    # Stage 2
    matches = identifier.identify(raw)
    if not matches:
        raise ResolverError("No matches found")
    
    # Stage 3
    identified = matches[0]
    completed = completer.complete(identified)
    
    # Stage 4
    formatted = formatter.format(completed, "bibtex")
    print(formatted)

Batch Processing
----------------

::

    from onecite import PipelineController
    
    controller = PipelineController()
    
    references = [
        "10.1038/nature14539",
        "1706.03762",
        "Smith (2020) Machine Learning"
    ]
    
    result = controller.process(
        input_content="\n\n".join(references),
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda candidates: 0
    )
    
    print(f"Processed: {result['report']['succeeded']}")
    print(f"Failed: {len(result['report']['failed_entries'])}")

Performance Optimization
------------------------

**Single Reference:**

::

    # Fast path for single reference
    result = process_references(
        input_content="10.1038/nature14539",
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda c: 0
    )

**Batch References:**

::

    # --quiet flag reduces output overhead
    onecite process refs.txt --quiet -o output.bib

**Large Batches:**

::

    # Split into chunks
    split -l 100 large_file.txt chunk_
    
    for chunk in chunk_*; do
        onecite process "$chunk" -o "${chunk}.bib" --quiet
    done

Error Handling in Pipeline
==========================

Validation Errors
-----------------

::

    from onecite import ValidationError
    
    try:
        result = process_references(
            input_content="",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda c: 0
        )
    except ValidationError:
        print("Empty input")

Resolution Errors
-----------------

::

    from onecite import ResolverError
    
    try:
        result = process_references(
            input_content="invalid/doi",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda c: 0
        )
    except ResolverError:
        print("Could not find reference")
        print("Check identifier or try again later")

Partial Success
---------------

::

    from onecite import process_references
    
    result = process_references(
        input_content=mixed_refs,
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=lambda c: 0
    )
    
    print(f"Success: {result['report']['succeeded']}")
    print(f"Failed: {len(result['report']['failed_entries'])}")
    
    if result['report']['failed_entries']:
        for entry in result['report']['failed_entries']:
            print(f"Failed entry {entry['id']}: {entry.get('error', 'Unknown')}")

Pipeline Configuration
======================

Custom Templates
----------------

::

    from onecite import PipelineController
    
    controller = PipelineController()
    controller.add_template_path("./my_templates")
    
    result = controller.process(
        entries=["10.1038/nature14539"],
        output_format="my_format"
    )

Data Source Priority
--------------------

::

    from onecite.pipeline import Identifier
    
    identifier = Identifier()
    
    # Set priority for specific query types
    identifier.set_source_priority(
        query_type="biomedical",
        sources=["pubmed", "crossref", "openalex"]
    )

Timeout Configuration
---------------------

::

    from onecite import PipelineController
    
    controller = PipelineController()
    controller.set_timeout(10)  # 10 seconds per query

Next Steps
----------

- See :doc:`../python_api` for usage examples
- Check :doc:`../api/core` for class reference
- Review :doc:`../advanced_usage` for complex scenarios
