# Contributing to jiraone

Thank you for your interest in contributing to jiraone! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/jiraone.git
   cd jiraone
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   # Or install dependencies manually:
   pip install requests pytest pytest-cov mypy black flake8
   ```

5. **Create a branch for your changes**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Use type hints for all public functions and methods
- Maximum line length: 88 characters (Black default)
- Use meaningful variable and function names

### Formatting

We use the following tools for code quality:

- **Black** for code formatting
- **flake8** for linting
- **mypy** for type checking

Before submitting a PR, run:
```bash
black src/jiraone
flake8 src/jiraone
mypy src/jiraone
```

### Docstrings

Use RST-style docstrings for all public classes and functions:

```python
def my_function(param1: str, param2: int = 0) -> dict:
    """Short description of the function.

    Longer description if needed, explaining the purpose
    and any important details.

    :param param1: Description of param1
    :param param2: Description of param2 (default: 0)

    :return: Description of what is returned

    :raises ValueError: When param1 is empty

    Example::

        result = my_function("test", param2=5)
        print(result)
    """
```

## Making Changes

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable

Good examples:
```
Add retry logic for rate-limited requests
Fix OAuth token refresh issue
Update documentation for endpoint methods
```

### Testing

- Write tests for new functionality
- Ensure all existing tests pass before submitting
- Aim for good test coverage

Run tests with:
```bash
pytest
# With coverage:
pytest --cov=src/jiraone --cov-report=html
```

### Documentation

- Update docstrings for any changed functions
- Update README.md if adding new features
- Add examples for new functionality

## Pull Request Process

1. **Ensure your code follows the style guidelines**

2. **Write or update tests** for your changes

3. **Update documentation** as needed

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub:
   - Provide a clear title and description
   - Reference any related issues
   - Describe what changes you made and why

6. **Address review feedback** promptly

### PR Checklist

Before submitting, verify:

- [ ] Code follows the project style guidelines
- [ ] All tests pass locally
- [ ] New functionality includes tests
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up to date with main

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- Python version
- jiraone version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Any error messages or stack traces

### Feature Requests

For feature requests, please describe:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Project Structure

```
jiraone/
├── src/jiraone/
│   ├── __init__.py      # Package exports
│   ├── access.py        # Authentication and HTTP client
│   ├── exceptions.py    # Exception classes
│   ├── reporting.py     # Report generation
│   ├── management.py    # User management
│   ├── module.py        # Utility functions
│   ├── utils.py         # Helper classes
│   └── jira_logs.py     # Logging configuration
├── docs/                # Sphinx documentation
├── tests/               # Test suite
└── examples/            # Usage examples
```

## Questions?

If you have questions about contributing, feel free to:

- Open a GitHub issue
- Check existing documentation
- Review the [Code of Conduct](CODE_OF_CONDUCT.md)

Thank you for contributing to jiraone!
