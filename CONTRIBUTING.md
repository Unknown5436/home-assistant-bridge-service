# Contributing to Home Assistant Bridge Service

Thank you for your interest in contributing to the Home Assistant Bridge Service! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Git
- Docker (optional)
- Home Assistant instance for testing

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/home-assistant-bridge-service.git
   cd home-assistant-bridge-service
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

4. **Set up environment:**
   ```bash
   cp env.example .env
   # Edit .env with your test configuration
   ```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run with verbose output
pytest -v
```

### Test Guidelines

- Write tests for new functionality
- Ensure tests are deterministic and don't depend on external services
- Use mocking for external API calls
- Aim for >80% code coverage
- Follow the existing test structure

## 📝 Code Style

### Python Standards

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Use meaningful variable and function names
- Keep functions small and focused
- Add docstrings for all public functions and classes

### Code Formatting

```bash
# Format code (if black is installed)
black app/ tests/

# Check linting (if flake8 is installed)
flake8 app/ tests/
```

### Commit Messages

Use conventional commit format:

```
type(scope): description

feat(auth): add JWT token support
fix(cache): resolve TTL calculation bug
docs(api): update endpoint documentation
test(client): add WebSocket connection tests
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## 🔄 Pull Request Process

### Before Submitting

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write code following the style guidelines
   - Add tests for new functionality
   - Update documentation if needed

3. **Test your changes:**
   ```bash
   pytest
   python start.py  # Test manually
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

### Submitting a Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request:**
   - Use a clear, descriptive title
   - Provide a detailed description of changes
   - Link any related issues
   - Include screenshots for UI changes

3. **PR Requirements:**
   - All tests must pass
   - Code coverage should not decrease
   - Documentation updated if needed
   - No merge conflicts

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment details:** OS, Python version, dependencies
- **Steps to reproduce:** Clear, numbered steps
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happens
- **Error messages:** Full error logs
- **Screenshots:** If applicable

## 💡 Feature Requests

For feature requests, please:

- Check existing issues first
- Provide a clear use case
- Explain the expected behavior
- Consider implementation complexity
- Be open to discussion and alternatives

## 📚 Documentation

### Code Documentation

- Use docstrings for all public functions and classes
- Follow Google or NumPy docstring format
- Include parameter types and return types
- Provide usage examples for complex functions

### API Documentation

- Update README.md for new endpoints
- Include request/response examples
- Document authentication requirements
- Add error code explanations

## 🔒 Security

### Security Guidelines

- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate all user inputs
- Follow security best practices
- Report security issues privately

### Security Issues

For security vulnerabilities, please:

- **DO NOT** create public issues
- Email security concerns privately
- Provide detailed reproduction steps
- Allow time for fixes before disclosure

## 🏷️ Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Version bumped
- [ ] Changelog updated
- [ ] Docker images built
- [ ] Release notes prepared

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different opinions and approaches
- Keep discussions on-topic

### Getting Help

- Check existing issues and discussions
- Ask questions in GitHub Discussions
- Join our community channels
- Be patient and provide context

## 📞 Contact

- **Issues:** [GitHub Issues](https://github.com/Unknown5436/home-assistant-bridge-service/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Unknown5436/home-assistant-bridge-service/discussions)
- **Security:** Contact maintainers privately

## 🙏 Recognition

Contributors will be recognized in:

- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to the Home Assistant Bridge Service! 🎉
