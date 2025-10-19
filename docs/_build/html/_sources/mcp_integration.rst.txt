automation Assistant Integration with MCP
=================================

OneCite provides full support for the Model Context Protocol (MCP), enabling MCP clients to directly use its citation management capabilities.

What is MCP?
-----------

The Model Context Protocol (MCP) is an open standard for connecting MCP clients with external tools and data sources. This allows MCP clients like MCP client to access OneCite's functionality seamlessly.

Installation and Setup
----------------------

1. Install OneCite
~~~~~~~~~~~~~~~~~~

::

    pip install onecite

2. Test the MCP Server
~~~~~~~~~~~~~~~~~~~~~~

::

    onecite-mcp

You should see output confirming the MCP server is running.

Configuring MCP desktop client
---------------------------

To use OneCite with MCP desktop client:

1. Open ``claude_desktop_config.json`` (usually located at ``~/.config/MCP client/claude_desktop_config.json``)

2. Add OneCite to the MCP servers configuration::

    {
      "mcpServers": {
        "onecite": {
          "command": "onecite-mcp"
        }
      }
    }

3. Restart MCP desktop client

4. Start a new conversation and OneCite will be available

Configuring editor client Editor
--------------------------

For editor client editor integration:

1. Open `.cursor/settings.json` (or create it if it doesn't exist)

2. Add OneCite configuration::

    {
      "mcpServers": {
        "onecite": {
          "command": "onecite-mcp"
        }
      }
    }

3. Restart editor client

4. OneCite will now be available in the MCP tools

Available Functions
-------------------

The OneCite MCP server provides the following functions:

cite
~~~~

Generate a single citation in various formats.

**Example Usage:**

- "Generate an APA citation for DOI: 10.1038/nature14539"
- "Create a BibTeX entry for the paper titled 'Attention is All You Need'"
- "Get a citation for arXiv:2103.00020 in MLA format"

**Parameters:**

- ``source`` - The paper identifier (DOI, title, arXiv ID, etc.)
- ``style`` - Output format: "bibtex", "apa", or "mla" (default: "bibtex")

batch_cite
~~~~~~~~~~

Process multiple references at once.

**Example Usage:**

- "Batch process these references in BibTeX format: [list of papers]"
- "Convert this list of authors and years to APA citations"
- "Process my references.txt file and give me BibTeX output"

**Parameters:**

- ``sources`` - List of paper identifiers or references
- ``style`` - Output format: "bibtex", "apa", or "mla" (default: "bibtex")

Example Conversations
---------------------

Example 1: Simple Citation Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**User:** "Can you generate a citation for the Deep Learning paper by LeCun, Bengio, and Hinton?"

**MCP client:** "I'll generate a citation for that paper."

*Uses the cite function to retrieve and format the citation*

**Output:**

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
      publisher = "Springer Science and Business Media LLC"
    }

Example 2: Batch Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**User:** "I have these papers to cite. Can you get BibTeX for all of them?
- 10.1038/nature14539
- 1706.03762 (arXiv)
- Deep Learning textbook by Goodfellow, Bengio, and Courville"

**MCP client:** "I'll process all three of those for you in BibTeX format."

*Uses batch_cite function*

**Output:**

::

    [BibTeX entries for all three references]

Example 3: Format Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**User:** "I need to convert my paper's bibliography to APA format. Here are the references..."

**MCP client:** "I'll convert those to APA format for you."

*Uses batch_cite with format="apa"*

**Output:**

::

    LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.
    [Additional APA citations...]

Troubleshooting
---------------

MCP Server Not Starting
~~~~~~~~~~~~~~~~~~~~~~~

If you see an error when running ``onecite-mcp``, try:

::

    # Check if OneCite is installed
    pip install --upgrade onecite
    
    # Test the installation
    onecite --version

MCP desktop client Not Recognizing OneCite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Check that the config file is in the correct location
2. Verify the JSON syntax is valid (use a JSON validator)
3. Restart MCP desktop client completely
4. Check that OneCite MCP server is responding::

    onecite-mcp --test

editor client Not Finding OneCite Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Ensure editor client is restarted after updating `.cursor/settings.json`
2. Verify the command path is correct
3. Try running ``onecite-mcp`` manually to check for errors

Advanced Configuration
----------------------

Custom Command Path
~~~~~~~~~~~~~~~~~~~

If OneCite is installed in a specific virtual environment, you can specify the full path::

    {
      "mcpServers": {
        "onecite": {
          "command": "/path/to/venv/bin/onecite-mcp"
        }
      }
    }

Error Logging
~~~~~~~~~~~~~

To debug MCP issues, check the MCP client's debug logs or MCP server logs.

Best Practices
--------------

1. **Be Specific** - Provide complete information (DOI, title, authors) for best results
2. **One at a Time** - For complex citations, process one or two at a time
3. **Verify Results** - Always check the output matches your needs
4. **Use Batch Processing** - For multiple references, batch_cite is more efficient
5. **Format Consistency** - Specify your desired format to avoid back-and-forth conversions

Integration with Workflows
---------------------------

With MCP client/editor client
~~~~~~~~~~~~~~~~~~

1. Discuss your research during conversation
2. Ask MCP client to generate citations as needed
3. Copy the formatted bibliography into your paper
4. Use for real-time citation help while writing

Workflow Example
~~~~~~~~~~~~~~~~

::

    User: "I'm writing about deep learning. Can you help me cite the foundational papers?"
    MCP client: "I'll help you cite the key deep learning papers. Let me get those for you."
    [MCP client uses batch_cite with deep learning papers]
    User: "Great! Can I get those in APA format instead?"
    MCP client: "Of course, let me convert those to APA."
    [MCP client uses batch_cite with format="apa"]

Next Steps
----------

- See :doc:`quick_start` for basic usage
- Learn :doc:`python_api` for programmatic access
- Check :doc:`templates` for customizing output format
