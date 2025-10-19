Contributing to OneCite
=======================

Thank you for your interest in contributing to OneCite! This guide will help you get started.

Getting Started
---------------

1. Fork the Repository
~~~~~~~~~~~~~~~~~~~~~~

Click the "Fork" button on the GitHub repository page.

2. Clone Your Fork
~~~~~~~~~~~~~~~~~~

::

    git clone https://github.com/your-username/OneCite.git
    cd OneCite

3. Create a Branch
~~~~~~~~~~~~~~~~~~

::

    git checkout -b feature/your-feature-name
    # or for bug fixes
    git checkout -b fix/issue-description

4. Set Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    
    # Install dependencies
    pip install -e ".[dev]"

Development Workflow
--------------------

Code Style
~~~~~~~~~~

We follow PEP 8 style guidelines. Use ``black`` for formatting::

    black onecite/ tests/

Linting
~~~~~~~

Use ``flake8`` to check code quality::

    flake8 onecite/ tests/

Running Tests
~~~~~~~~~~~~~

Run the test suite::

    pytest tests/

Check coverage::

    pytest --cov=onecite tests/

Creating Commits
~~~~~~~~~~~~~~~~

Write clear, descriptive commit messages::

    # Good
    git commit -m "Add support for custom templates"
    
    # Bad
    git commit -m "Fix stuff"

Use the imperative mood: "Add feature" not "Added feature"

Types of Contributions
----------------------

Bug Reports
~~~~~~~~~~~

Before submitting a bug report:

1. Check existing issues to avoid duplicates
2. Include your Python and OneCite version
3. Provide a minimal code example to reproduce
4. Describe expected vs actual behavior

**Template:**

::

    **Describe the bug**
    [Description of the bug]
    
    **To Reproduce**
    [Steps to reproduce]
    
    **Expected behavior**
    [What should happen]
    
    **Actual behavior**
    [What actually happens]
    
    **Environment**
    - Python version: 3.x.x
    - OneCite version: 0.x.x
    - OS: Windows/macOS/Linux

Feature Requests
~~~~~~~~~~~~~~~~

Describe:

1. What problem it solves
2. How it would be used
3. Any alternative approaches

**Template:**

::

    **Is your feature request related to a problem?**
    [Describe the problem]
    
    **Describe the solution**
    [Describe the proposed solution]
    
    **Describe alternatives considered**
    [Alternative solutions or features]

Code Contributions
~~~~~~~~~~~~~~~~~~

1. Small Fixes
^^^^^^^^^^^^^^

For typos, documentation, or small bugs:

1. Create a branch
2. Make the change
3. Test thoroughly
4. Submit a PR with clear description

2. New Features
^^^^^^^^^^^^^^^

For larger features:

1. Open an issue first to discuss
2. Wait for feedback from maintainers
3. Once approved, implement
4. Include tests and documentation
5. Submit PR

3. Bug Fixes
^^^^^^^^^^^^

For bug fixes:

1. Open an issue describing the bug
2. Create a branch from the issue
3. Include a test that demonstrates the bug
4. Implement the fix
5. Ensure the test now passes

Documentation Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~

Documentation is crucial! Contributions include:

- Fixing typos
- Clarifying explanations
- Adding examples
- Improving API documentation
- Translating documentation

Submit documentation changes as PRs to the repository.

Submitting a Pull Request
--------------------------

1. **Push to Your Fork**

::

    git push origin feature/your-feature-name

2. **Create a Pull Request**

Go to GitHub and click "New Pull Request"

3. **PR Description**

Include:

- What change does it make?
- Why is this change needed?
- How has it been tested?
- Any breaking changes?

**Template:**

::

    ## Description
    [Brief description of changes]
    
    ## Related Issues
    Closes #123
    
    ## Type of Change
    - [ ] Bug fix
    - [ ] New feature
    - [ ] Documentation
    - [ ] Other
    
    ## Testing
    [Describe testing performed]
    
    ## Checklist
    - [ ] Tests pass
    - [ ] Code follows style guidelines
    - [ ] Documentation updated
    - [ ] No breaking changes

4. **Code Review**

A maintainer will review your PR. Be prepared to:

- Discuss implementation
- Address feedback
- Make requested changes
- Ensure tests pass

5. **Merge**

Once approved, a maintainer will merge your PR.

Testing Guidelines
------------------

Writing Tests
~~~~~~~~~~~~~

Tests should be:

- **Isolated** - Not dependent on other tests
- **Clear** - Easy to understand intent
- **Focused** - Test one thing
- **Fast** - Complete quickly

**Example:**

::

    def test_process_references_with_doi():
        result = process_references(
            input_content="10.1038/nature14539",
            input_type="txt"
        )
        assert result['processed_count'] == 1
        assert '10.1038/nature14539' in result['output_content']

Running Tests
~~~~~~~~~~~~~

::

    # Run all tests
    pytest
    
    # Run specific test file
    pytest tests/test_cli.py
    
    # Run specific test
    pytest tests/test_cli.py::test_process_command
    
    # Run with coverage
    pytest --cov=onecite

Documentation Guidelines
-------------------------

Code Comments
~~~~~~~~~~~~~

- Add docstrings to all functions and classes
- Use Google-style docstrings

::

    def process_references(input_content, input_type="txt"):
        """Process references and return formatted bibliography.
        
        Args:
            input_content (str): The reference content to process
            input_type (str): Type of input - "txt" or "bib"
        
        Returns:
            dict: Dictionary with output_content, processed_count, etc.
        
        Raises:
            ValidationError: If input is invalid
            ParseError: If parsing fails
        """

API Documentation
~~~~~~~~~~~~~~~~~

Update docstrings when changing:

- Function signatures
- Parameters
- Return values
- Exceptions
- Behavior

Release Process
---------------

Versioning
~~~~~~~~~~

OneCite follows `Semantic Versioning <https://semver.org/>`_:

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

Community Standards
-------------------

Code of Conduct
~~~~~~~~~~~~~~~

- Be respectful
- Be inclusive
- Provide constructive feedback
- Accept criticism gracefully
- Report inappropriate behavior

Communication
~~~~~~~~~~~~~

- Use clear, professional language
- Be patient with new contributors
- Assume good intentions
- Help educate when needed

Project Leadership
~~~~~~~~~~~~~~~~~~

The OneCite Team:

- Makes final decisions on features and releases
- Reviews and merges PRs
- Maintains project standards
- Responds to issues and discussions

Getting Help
~~~~~~~~~~~~

- Check existing documentation
- Search closed issues and PRs
- Ask in GitHub Discussions
- Contact maintainers if needed

Additional Resources
--------------------

- `GitHub Flow Guide <https://guides.github.com/introduction/flow/>`_
- `PEP 8 Style Guide <https://www.python.org/dev/peps/pep-0008/>`_
- `Semantic Versioning <https://semver.org/>`_
- `Conventional Commits <https://www.conventionalcommits.org/>`_

Recognition
-----------

Contributors are recognized in:

- Release notes
- README acknowledgments
- GitHub contributors page

Thank you for making OneCite better!

Next Steps
----------

- Check the issues page for `good first issues <https://github.com/HzaCode/OneCite/labels/good%20first%20issue>`_
- Read existing code and tests
- Start with documentation or small fixes
- Ask questions in discussions
