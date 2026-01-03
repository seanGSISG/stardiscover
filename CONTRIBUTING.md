# Contributing to StarDiscover

Thank you for your interest in contributing to StarDiscover! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/seanGSISG/stardiscover/issues) to avoid duplicates
2. Create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Relevant logs or screenshots

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would benefit other users

### Submitting Code

#### Setup Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/stardiscover.git
cd stardiscover

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

#### Development Workflow

1. Create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style guidelines

3. Test your changes:
   ```bash
   pytest
   ```

4. Commit with clear messages:
   ```bash
   git commit -m "Add feature: description of what you added"
   ```

5. Push and create a pull request

#### Pull Request Guidelines

- Reference any related issues
- Describe what changes you made and why
- Include screenshots for UI changes
- Ensure all tests pass
- Keep PRs focused on a single change

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints for function parameters and return values
- Write docstrings for public functions and classes
- Maximum line length: 100 characters

### HTML/Templates

- Use consistent indentation (2 spaces)
- Keep templates readable and well-organized

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Keep the first line under 72 characters
- Reference issues when applicable (`Fix #123`)

## Project Structure

```
stardiscover/
├── app/
│   ├── main.py          # Application entry point
│   ├── config.py        # Configuration management
│   ├── database.py      # Database setup
│   ├── models/          # SQLAlchemy models
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic
│   ├── tasks/           # Background tasks
│   └── templates/       # Jinja2 templates
├── tests/               # Test files
├── docs/                # Documentation
└── data/                # Runtime data (gitignored)
```

## Testing

- Write tests for new features
- Maintain or improve test coverage
- Run the full test suite before submitting PRs

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app
```

## Questions?

Feel free to open an issue for any questions about contributing.
