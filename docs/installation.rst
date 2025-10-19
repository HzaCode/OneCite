Installation Guide
==================

System Requirements
-------------------

- Python 3.7 or higher
- pip package manager
- Internet connection (for accessing data sources)

Installing from PyPI (Recommended)
----------------------------------

The easiest way to install OneCite is from the Python Package Index (PyPI)::

    pip install onecite

This will install OneCite and all required dependencies.

Installing from Source
----------------------

If you want to install a development version from source::

    git clone https://github.com/HzaCode/OneCite.git
    cd OneCite
    pip install -e ".[dev]"

The ``-e`` flag installs the package in editable mode, which is useful for development.

Optional Dependencies
---------------------

For development and testing, install development dependencies::

    pip install onecite[dev]

This will install the following additional packages:

- pytest - Testing framework
- pytest-cov - Coverage reporting
- flake8 - Code style checking
- black - Code formatting tool

Verifying the Installation
---------------------------

To verify that your installation was successful, run::

    onecite --version

You should see the version number printed.

MCP Server
----------

OneCite includes a Model Context Protocol (MCP) server. To test it::

    onecite-mcp

This will start the MCP server. You can now configure your MCP client to use it. For more details, see :doc:`mcp_integration`.

Upgrading OneCite
-----------------

To upgrade to the latest version::

    pip install --upgrade onecite

Troubleshooting
---------------

Dependency Conflicts
~~~~~~~~~~~~~~~~~~~~

If you encounter dependency conflicts during installation, try::

    pip install --upgrade pip setuptools wheel

Then reinstall OneCite.

Permission Errors
~~~~~~~~~~~~~~~~~

If you get permission errors on macOS or Linux, try using the ``--user`` flag::

    pip install --user onecite

Or consider using a virtual environment (recommended).

Virtual Environments (Recommended)
----------------------------------

Using a virtual environment helps avoid system-wide package conflicts::

    # Create a virtual environment
    python -m venv venv
    
    # Activate the virtual environment
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows:
    venv\Scripts\activate
    
    # Install OneCite
    pip install onecite
    
    # Deactivate the virtual environment when done
    deactivate

Next Steps
----------

After installation, see :doc:`quick_start` to get started with OneCite.
