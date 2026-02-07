# Configuration file for the Sphinx documentation builder.

import os
import sys

# Add the parent directory to the path so we can import onecite
sys.path.insert(0, os.path.abspath('..'))

from onecite import __version__

# Project information
project = 'OneCite'
copyright = '2024, OneCite Team'
author = 'OneCite Team'
release = __version__

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Default options for autodoc
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': False,
    'show-inheritance': True,
}

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://docs.python-requests.org/en/latest', None),
}

# HTML output configuration
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = '../logo_.jpg'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
}

# LaTeX output configuration
latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
}

# Man page output configuration
man_pages = [
    ('cli', 'onecite', 'Citation and academic reference toolkit', ['OneCite Team'], 1)
]

# Texinfo output configuration
texinfo_documents = [
    ('index', 'OneCite', 'Citation & Academic Reference Toolkit',
     'OneCite Team', 'OneCite', 'Automate academic reference management', 'Miscellaneous'),
]

# Source file parsing
source_suffix = '.rst'
master_doc = 'index'

# Syntax highlighting
pygments_style = 'sphinx'

# Language
language = 'en'

# Remove warnings for missing references
suppress_warnings = ['ref.doc']
