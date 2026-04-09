# Contributing to OneCite

Thank you for your interest in contributing to OneCite! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to the Contributor Covenant [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to ang@hezhiang.com.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/OneCite.git
   cd OneCite
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/HzaCode/OneCite.git
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip

### Install Development Dependencies

```bash
# Install the package in editable mode with development dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run tests to verify everything is working
pytest

# Check code style
flake8 onecite tests
```

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with:

- A clear, descriptive title
- Steps to reproduce the problem
- Expected behavior vs. actual behavior
- Your environment (OS, Python version, OneCite version)
- Any relevant logs or error messages

### Suggesting Enhancements

Feature requests are welcome! Please create an issue with:

- A clear description of the feature
- Why this feature would be useful
- Any implementation ideas you have

### Contributing Code

1. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes** following our [Coding Standards](#coding-standards)

3. **Add or update tests** for your changes

4. **Update documentation** if needed

5. **Run tests** to ensure everything works:
   ```bash
   pytest
   pytest --cov=onecite  # Check coverage
   ```

6. **Commit your changes** with a clear commit message:
   ```bash
   git commit -m "feat: add support for new citation format"
   # or
   git commit -m "fix: resolve DOI parsing issue"
   ```

## Pull Request Process

1. **Update your fork** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub with:
   - A clear title and description
   - Reference to any related issues
   - Screenshots or examples if applicable

4. **Address review comments** promptly

5. **Ensure CI passes** - all tests must pass before merging

### PR Title Convention

Use conventional commits format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `style:` - Code style changes (formatting, etc.)
- `chore:` - Maintenance tasks

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) style guide. Key points:

- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use descriptive variable and function names
- Add docstrings to all public functions and classes

### Type Hints

Use type hints where possible:

```python
def process_doi(doi: str) -> Dict[str, Any]:
    """Process a DOI and return citation data."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When invalid input is provided
    """
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core.py

# Run with coverage
pytest --cov=onecite --cov-report=html

# Run verbose mode
pytest -v
```

### Writing Tests

- Write tests for all new features and bug fixes
- Aim for >80% code coverage
- Use descriptive test function names
- Include docstrings explaining what the test does
- Use fixtures for common setup

Example:

```python
def test_doi_parsing_valid_format():
    """Test that valid DOI formats are parsed correctly."""
    doi = "10.1038/nature14539"
    result = parse_doi(doi)
    assert result is not None
    assert result['prefix'] == "10.1038"
```

## Documentation

### Code Documentation

- Add docstrings to all public functions, classes, and modules
- Keep docstrings up-to-date with code changes
- Include examples in docstrings when helpful

### User Documentation

Documentation is in the `docs/` directory using reStructuredText format:

```bash
# Build documentation
cd docs
make html

# View documentation
open _build/html/index.html
```

### README Updates

Update README.md if your changes:

- Add new features
- Change installation process
- Modify usage examples
- Add new dependencies

## Questions?

If you have questions or need help:

- Open an issue on GitHub
- Check existing issues and documentation
- Email ang@hezhiang.com

Thank you for contributing to OneCite! 🎉

