# OneCite Documentation

Welcome to the OneCite documentation source. This directory contains the reStructuredText (RST) source files for the complete OneCite documentation built with Sphinx.

## Building the Documentation

### Prerequisites

Install the required documentation dependencies:

```bash
pip install -e ".[dev]"
# or
pip install sphinx sphinx-rtd-theme
```

### Building HTML Documentation

To build the documentation as HTML:

```bash
# On Linux/macOS
make html

# On Windows (if make is not available)
sphinx-build -b html . _build/html
```

The built documentation will be in `_build/html/`. Open `_build/html/index.html` in your browser to view it.

### Building Other Formats

**PDF:**
```bash
make latexpdf
```

**Man Pages:**
```bash
make man
```

**Texinfo:**
```bash
make texinfo
```

**Epub:**
```bash
make epub
```

### Cleaning Build Files

To remove all built documentation:

```bash
make clean
```

## File Structure

```
docs/
├── conf.py                      # Sphinx configuration
├── index.rst                    # Main documentation index
├── installation.rst             # Installation guide
├── quick_start.rst              # Quick start guide
├── basic_usage.rst              # Basic usage guide
├── advanced_usage.rst           # Advanced usage guide
├── python_api.rst               # Python API guide
├── mcp_integration.rst          # MCP integration guide
├── templates.rst                # Custom templates guide
├── output_formats.rst           # Output formats guide
├── faq.rst                      # Frequently asked questions
├── contributing.rst             # Contributing guidelines
├── changelog.rst                # Version changelog
├── api/
│   ├── core.rst                # Core API reference
│   ├── exceptions.rst          # Exception reference
│   └── pipeline.rst            # Pipeline reference
├── Makefile                     # Build automation
└── README.md                    # This file
```

## Documentation Sections

### Getting Started
- **installation.rst** - How to install OneCite
- **quick_start.rst** - Get started in 5 minutes
- **basic_usage.rst** - Basic usage examples

### User Guides
- **advanced_usage.rst** - Advanced features and techniques
- **python_api.rst** - Using OneCite as a Python library
- **mcp_integration.rst** - MCP client integration
- **templates.rst** - Creating custom citation templates
- **output_formats.rst** - Understanding output formats

### Reference
- **api/core.rst** - Core API documentation
- **api/exceptions.rst** - Exception reference
- **api/pipeline.rst** - Pipeline processing reference

### Additional
- **faq.rst** - Frequently asked questions
- **contributing.rst** - Contribution guidelines
- **changelog.rst** - Version history and roadmap

## Writing Documentation

### RST Basics

Documentation is written in reStructuredText (RST) format. Here are some basics:

```rst
Main Section
============

Subsection
----------

Subsubsection
~~~~~~~~~~~~~

**Bold text** and *italic text*

.. code-block:: python

    # Code block
    import onecite
    
    result = onecite.process_references("10.1038/nature14539")

- Bullet list
- Another item
  - Nested item

1. Numbered list
2. Second item

:doc:`Link to file`
`External link <https://example.com>`_
```

### Adding New Pages

1. Create a new `.rst` file in the appropriate directory
2. Add it to the `.. toctree::` directive in `index.rst` or a parent document
3. Build the docs to verify

### Code Examples

Use `.. code-block::` for syntax-highlighted code:

```rst
.. code-block:: python

    from onecite import process_references
    
    result = process_references("10.1038/nature14539")
    print(result['output_content'])
```

## Configuration

The Sphinx configuration is in `conf.py`. Key settings:

- **Extensions** - Enabled Sphinx extensions for autodoc, intersphinx, etc.
- **Theme** - Using the ReadTheDocs theme (sphinx-rtd-theme)
- **HTML Output** - Settings for the HTML theme
- **Autodoc** - Automatic API documentation generation

## Continuous Integration

Documentation builds automatically on:

- GitHub Commits
- Pull Requests
- Releases

## Hosting

The documentation is hosted at:

- **Development:** docs.example.com (built from main branch)
- **Latest:** docs.example.com/stable (built from latest release)

## Contributing to Documentation

1. Fork the repository
2. Create a branch for your changes
3. Edit `.rst` files
4. Build locally to verify: `make html`
5. Submit a pull request

See **contributing.rst** for more details.

## Linking

To create links within documentation:

```rst
:doc:`quick_start`           # Link to another document
:ref:`genindex`              # Link to generated index
:meth:`~onecite.process_references`  # Link to methods
:class:`~onecite.RawEntry`           # Link to classes
```

## Tables and Lists

**Tables:**

```rst
==========  ============
Header 1    Header 2
==========  ============
Cell 1      Cell 2
Cell 3      Cell 4
==========  ============
```

**Lists:**

```rst
- Item 1
- Item 2
  - Subitem 2.1
  - Subitem 2.2
- Item 3
```

## Tips

- Run `make html` frequently while editing
- Use `sphinx-build -W` to treat warnings as errors
- Use `make linkcheck` to verify all links
- Keep lines under 80 characters for easier reviewing

## Troubleshooting

**"make: command not found" on Windows:**
```bash
# Install make for Windows or use sphinx-build directly
sphinx-build -b html . _build/html
```

**Module not found errors:**
```bash
# Ensure you're in the docs directory
cd docs

# Rebuild the documentation
make clean
make html
```

**Theme not found:**
```bash
# Install the theme
pip install sphinx-rtd-theme
```

## Support

For documentation issues:

1. Check the [GitHub Issues](https://github.com/HzaCode/OneCite/issues)
2. Search [GitHub Discussions](https://github.com/HzaCode/OneCite/discussions)
3. See :doc:`faq` for common questions

## License

The OneCite documentation is licensed under the MIT License. See LICENSE for details.

---

Happy documenting! 📚
