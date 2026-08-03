# Configuration file for the Sphinx documentation builder.

from onecite import __version__

# Project information
project = "OneCite"
copyright = "2025, OneCite Team"
author = "OneCite Team"
release = __version__

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Default options for autodoc
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": False,
    "show-inheritance": True,
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://docs.python-requests.org/en/latest", None),
}

# HTML output configuration
html_theme = "sphinx_rtd_theme"
html_static_path = []
html_logo = "../logo_.jpg"
html_theme_options = {
    "logo_only": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "#2980B9",
}

# LaTeX output configuration
latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
}

# Man page output configuration
man_pages = [("cli", "onecite", "Auditable citation normalization toolkit", ["OneCite Team"], 1)]

# Texinfo output configuration
texinfo_documents = [
    (
        "index",
        "OneCite",
        "Auditable Citation Normalization",
        "OneCite Team",
        "OneCite",
        "Normalize scholarly references with auditable source resolution",
        "Miscellaneous",
    ),
]

# Source file parsing
source_suffix = ".rst"
master_doc = "index"

# Syntax highlighting
pygments_style = "sphinx"

# Language
language = "en"

# Remove warnings for missing references
suppress_warnings = ["ref.doc"]
