# Contributing to Distributed Vision System

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Test thoroughly
6. Commit with clear messages
7. Push to your fork
8. Create a Pull Request

## Development Setup

### Prerequisites
- Python 3.10+
- Conda/Miniconda
- For RPi development: Raspberry Pi 5 with cameras
- For WSL development: Ubuntu on WSL with NVIDIA GPU

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd kebak_sorting

# Setup RPi environment
cd rpi
conda env create -f environment.yml
conda activate rpi-vision

# Setup WSL environment
cd ../wsl
conda env create -f environment.yml
conda activate wsl-vision
```

## Code Style

### Python
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings to functions and classes

### Example
```python
def process_frame(frame: np.ndarray, config: dict) -> dict:
    """
    Process a single frame with the given configuration.
    
    Args:
        frame: Input frame as numpy array
        config: Processing configuration dictionary
        
    Returns:
        dict: Processing results including detections and metadata
    """
    # Implementation
    pass
```

## Testing

### Unit Tests
```bash
# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_rpi.py

# With coverage
python -m pytest --cov=src tests/
```

### Integration Tests
```bash
# Test full pipeline
python -m pytest tests/test_integration.py -v
```

### Manual Testing
- Test camera capture independently
- Verify UDP transmission/reception
- Check YOLO inference accuracy
- Validate API endpoints
- Test dashboard functionality

## Pull Request Process

1. **Update Documentation**: Keep README and docs current
2. **Add Tests**: Include tests for new features
3. **Check Style**: Run linting tools
4. **Test Thoroughly**: Ensure all tests pass
5. **Write Clear Commits**: Descriptive commit messages
6. **Update CHANGELOG**: Document your changes

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No breaking changes
```

## Areas for Contribution

### High Priority
- [ ] H.264 hardware encoding on RPi
- [ ] Additional YOLO model support (YOLOv9, YOLOv10)
- [ ] Advanced fusion algorithms (Bayesian fusion)
- [ ] Mobile app for monitoring
- [ ] Docker containerization

### Medium Priority
- [ ] Multi-camera support (>2 cameras)
- [ ] Recording and playback features
- [ ] Alert system (email, SMS)
- [ ] Advanced analytics dashboard
- [ ] Performance benchmarking tools

### Low Priority
- [ ] Alternative object detection models
- [ ] Cloud deployment options
- [ ] Load balancing for multiple RPi devices
- [ ] Database integration
- [ ] User authentication

## Bug Reports

### Template
```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- OS: [e.g., Raspberry Pi OS, Ubuntu on WSL]
- Python version:
- Conda environment:
- Hardware: [e.g., RPi 5, RTX 3080]

**Logs**
Relevant log excerpts

**Additional Context**
Any other relevant information
```

## Feature Requests

### Template
```markdown
**Feature Description**
Clear description of the proposed feature

**Use Case**
Why this feature would be useful

**Proposed Solution**
How you think it should work

**Alternatives**
Alternative solutions considered

**Additional Context**
Any other relevant information
```

## Code Review Guidelines

### For Reviewers
- Be constructive and respectful
- Focus on code quality and maintainability
- Test the changes locally if possible
- Provide specific feedback
- Approve or request changes clearly

### For Contributors
- Respond to feedback promptly
- Be open to suggestions
- Explain your approach if questioned
- Update based on feedback
- Request re-review when ready

## Versioning

We use [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open an issue for discussion
- Check existing issues and PRs
- Review documentation thoroughly

## Thank You!

Your contributions help make this project better for everyone. We appreciate your time and effort!
