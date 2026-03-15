# Contributing to SafeRoute

Thank you for considering contributing to SafeRoute! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Git Workflow](#git-workflow)
5. [Coding Standards](#coding-standards)
6. [Commit Guidelines](#commit-guidelines)
7. [Pull Request Process](#pull-request-process)
8. [Testing Requirements](#testing-requirements)
9. [Documentation](#documentation)
10. [Code Review](#code-review)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. We pledge to:

- Be respectful and inclusive of all backgrounds and identities
- Welcome constructive feedback and differing opinions
- Focus on collaboration and learning
- Report unacceptable behavior to the maintainers

### Expected Behavior

- Be professional and courteous
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or trolling
- Derogatory comments or personal attacks
- Public or private harassment
- Publishing private information without consent
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose (for local development)
- Git
- GitHub account

### Fork and Clone

```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/YOUR-USERNAME/SafeRouteV1-main.git
cd SafeRouteV1-main

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL-OWNER/SafeRouteV1-main.git

# Verify remotes
git remote -v
# origin: your fork
# upstream: main repository
```

---

## Development Setup

### Backend Setup

```bash
# Navigate to backend directory
cd SafeRoute_Backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Create .env file from template
cp ../.env.example .env

# Edit .env with your local settings
# SAFETY_API_KEY=dev-key-change-in-production
# DATABASE_URL=sqlite:///./saferoute.db
# REDIS_URL=redis://localhost:6379

# Run tests
pytest

# Start development server
uvicorn main:app --reload --port 8000
```

### Frontend (Admin Dashboard) Setup

```bash
# Navigate to admin directory
cd SafeRoute_Admin

# Install dependencies
npm install

# Install pre-commit hooks for frontend
npm run prepare

# Create environment file
cp .env.example .env

# Edit .env with backend URL
# VITE_API_URL=http://localhost:8000

# Start development server
npm run dev

# Access at http://localhost:5173
```

### Mobile App Setup

```bash
# Navigate to mobile directory
cd SafeRoute_Native

# Install dependencies
npm install

# Install Expo CLI
npm install -g expo-cli

# Create environment file
cp .env.example .env

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Or use Expo Go app
expo start
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild containers
docker-compose up -d --build
```

---

## Git Workflow

### Branch Naming Convention

Use the following format: `<type>/<description>`

**Types:**
- `feature/` - New feature (e.g., `feature/add-ml-predictions`)
- `bugfix/` - Bug fix (e.g., `bugfix/fix-route-calculation`)
- `enhancement/` - Performance or code improvement (e.g., `enhancement/optimize-database-queries`)
- `docs/` - Documentation (e.g., `docs/update-api-docs`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-safety-engine`)
- `test/` - Test additions (e.g., `test/add-websocket-tests`)
- `chore/` - Maintenance (e.g., `chore/update-dependencies`)

### Creating a Branch

```bash
# Ensure you're on main and up-to-date
git checkout main
git pull upstream main

# Create and checkout new branch
git checkout -b feature/your-feature-name

# Push branch to your fork
git push -u origin feature/your-feature-name
```

### Keeping Branch Updated

```bash
# Fetch latest from upstream
git fetch upstream

# Rebase your branch on upstream/main
git rebase upstream/main

# If conflicts, resolve them, then:
git add .
git rebase --continue

# Force push to your fork
git push -f origin feature/your-feature-name
```

---

## Coding Standards

### Python (Backend)

**Code Style:** PEP 8 using Black formatter

```bash
# Format code
black SafeRoute_Backend/

# Check style
flake8 SafeRoute_Backend/

# Check type hints
mypy SafeRoute_Backend/
```

**Pre-commit Configuration** (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.1.1
    hooks:
      - id: mypy
        additional_dependencies: ['types-all']

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

**Code Example:**

```python
"""Module docstring."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/routes", tags=["routes"])


class RouteRequest(BaseModel):
    """Request model for route calculation."""

    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    user_id: str


@router.post("/safest")
async def calculate_safest_route(
    request: RouteRequest,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Calculate the safest route between two points.

    Args:
        request: Route request with start and end coordinates
        api_key: Validated API key

    Returns:
        Dictionary with route details and safety score

    Raises:
        ValueError: If coordinates are invalid
        HTTPException: If route calculation fails
    """
    # Implementation here
    pass
```

### TypeScript/JavaScript (Frontend)

**Code Style:** ESLint + Prettier

```bash
# Format code
npm run format

# Check linting
npm run lint

# Fix linting issues
npm run lint:fix
```

**ESLint Configuration** (`.eslintrc.json`):

```json
{
  "extends": ["eslint:recommended", "plugin:react/recommended"],
  "rules": {
    "indent": ["error", 2],
    "quotes": ["error", "single"],
    "semi": ["error", "always"],
    "no-unused-vars": "error",
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  },
  "parserOptions": {
    "ecmaVersion": 2021,
    "sourceType": "module",
    "ecmaFeatures": { "jsx": true }
  }
}
```

**Code Example:**

```typescript
import { FC, useState } from 'react';
import { calculateRoute } from '../api/routes';

interface MapProps {
  startLocation: Coordinates;
  endLocation: Coordinates;
}

export const MapView: FC<MapProps> = ({ startLocation, endLocation }) => {
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCalculateRoute = async () => {
    setLoading(true);
    try {
      const result = await calculateRoute(startLocation, endLocation);
      setRoute(result);
    } catch (error) {
      console.error('Route calculation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="map-container">
      {/* JSX here */}
    </div>
  );
};
```

---

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Test additions/modifications
- `chore:` - Build process, dependencies, etc.

### Scope

Name of the component/module affected (optional):
- `api` - API routes
- `services` - Business logic services
- `mobile` - Mobile app
- `admin` - Admin dashboard
- `db` - Database related
- `auth` - Authentication

### Subject

- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at end
- Limit to 50 characters

### Body (Optional)

- Explain what and why, not how
- Wrap at 72 characters
- Separate from subject by blank line

### Footer (Optional)

- Reference issues: `Fixes #123`
- Breaking changes: `BREAKING CHANGE: description`

### Examples

```
feat(routes): add ML-based safety predictions

Implement machine learning model for predicting
route safety scores based on historical data.
Improves accuracy by 23% compared to rule-based engine.

Fixes #456
```

```
fix(api): handle missing API key gracefully

Previously returned 500 error when API key was missing.
Now returns 401 with clear error message.

Fixes #789
```

```
docs(readme): update installation instructions
```

---

## Pull Request Process

### Before Creating PR

1. **Update branch** from main:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**:
   ```bash
   # Backend
   pytest --cov=.
   black --check SafeRoute_Backend/
   flake8 SafeRoute_Backend/
   mypy SafeRoute_Backend/
   
   # Frontend
   npm run lint
   npm run test
   npm run build
   ```

3. **Test manually**:
   - Feature works as expected
   - No regressions in existing features
   - UI/UX is consistent
   - Performance is acceptable

### Creating a PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub**:
   - Title: Clear, descriptive, follows commit convention
   - Description: Fill out the PR template completely

### PR Template

```markdown
## Description
Brief description of changes

## Related Issue
Fixes #(issue number)

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Description of test cases

## Screenshots (if applicable)
Before/after screenshots

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Self-review completed
```

### Review Process

1. **Automated checks** must pass:
   - CI/CD pipeline
   - Code coverage requirements
   - Linting checks

2. **Code review** by maintainers:
   - Correctness
   - Performance
   - Security
   - Style compliance
   - Documentation quality

3. **Approval** required before merge
4. **Squash and merge** (for cleaner history)

---

## Testing Requirements

### Backend Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest --cov=. --cov-report=html tests/

# Specific test file
pytest tests/test_routes.py -v

# Specific test
pytest tests/test_routes.py::TestRouteCalculation::test_safest_route -v
```

**Test Coverage Target:** 80%+

**Test Structure:**
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestRouteCalculation:
    def test_valid_route_request(self):
        """Test route calculation with valid coordinates."""
        response = client.post(
            "/routes/safest",
            json={
                "start": {"lat": 17.44, "lng": 78.35},
                "end": {"lat": 17.45, "lng": 78.36},
                "user_id": "test-user"
            }
        )
        assert response.status_code == 200
    
    def test_invalid_coordinates(self):
        """Test route calculation with invalid coordinates."""
        response = client.post(
            "/routes/safest",
            json={
                "start": {"lat": 200, "lng": 400},
                "end": {"lat": 17.45, "lng": 78.36},
                "user_id": "test-user"
            }
        )
        assert response.status_code == 400
```

### Frontend Tests

```bash
# Run tests
npm run test

# With coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

**Test Example:**
```typescript
import { render, screen } from '@testing-library/react';
import { MapView } from '../MapView';

describe('MapView', () => {
  it('renders map component', () => {
    render(
      <MapView 
        startLocation={{ lat: 17.44, lng: 78.35 }}
        endLocation={{ lat: 17.45, lng: 78.36 }}
      />
    );
    
    expect(screen.getByTestId('map-container')).toBeInTheDocument();
  });
});
```

---

## Documentation

### Code Documentation

**Python:**
```python
def calculate_safety_score(segment: dict, hour: int) -> tuple[float, dict]:
    """
    Calculate safety score for a route segment.
    
    Args:
        segment: Dictionary with segment coordinates and metadata
        hour: Hour of day (0-23) for time-based analysis
    
    Returns:
        Tuple of (safety_score, impact_breakdown)
        where safety_score is 0-1 and impact_breakdown shows
        contribution of each factor
    
    Raises:
        ValueError: If coordinates are outside valid range
    
    Example:
        >>> score, impacts = calculate_safety_score(
        ...     {"lat": 17.44, "lng": 78.35, "crime_density": 0.3},
        ...     hour=14
        ... )
        >>> score
        0.85
    """
```

**TypeScript:**
```typescript
/**
 * Calculate optimal route between two locations
 * @param start - Starting coordinates
 * @param end - Ending coordinates
 * @param options - Route calculation options
 * @returns Promise with calculated route and metadata
 * @throws {RouteCalculationError} If route cannot be calculated
 */
async function calculateRoute(
  start: Coordinates,
  end: Coordinates,
  options?: RouteOptions
): Promise<RouteResult> {
  // Implementation
}
```

### PR Documentation

- Update README if needed
- Add/update API documentation
- Update ARCHITECTURE.md for structural changes
- Include migration guides for breaking changes
- Add examples for new features

---

## Code Review

### Reviewer Responsibilities

1. **Code Quality**
   - Follows style guidelines
   - Readable and maintainable
   - No code duplication
   - Proper error handling

2. **Functionality**
   - Solves the stated problem
   - Handles edge cases
   - No regression in existing features
   - Performance acceptable

3. **Security**
   - No security vulnerabilities
   - Proper input validation
   - Safe handling of credentials
   - No exposure of sensitive data

4. **Testing**
   - Tests are comprehensive
   - Coverage targets met
   - Edge cases covered
   - Tests are maintainable

5. **Documentation**
   - Code is well-documented
   - API documentation updated
   - User documentation updated
   - Commit messages are clear

### Providing Feedback

- Be constructive and respectful
- Ask questions rather than making demands
- Acknowledge good work
- Suggest improvements, not just criticisms
- Reference specific lines of code

### Addressing Feedback

- Respond to all comments
- Ask clarifying questions if needed
- Make requested changes or discuss alternatives
- Re-request review after changes

---

## Release Process

### Version Numbering

Follow Semantic Versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Steps

1. Update version in `package.json` and `pyproject.toml`
2. Update CHANGELOG.md
3. Tag release: `git tag v1.0.0`
4. Push tag: `git push upstream v1.0.0`
5. Build and publish artifacts
6. Create GitHub release with changelog

---

## Getting Help

- **GitHub Issues:** For bugs and feature requests
- **Discussions:** For questions and community discussion
- **Email:** For security issues (do not create public issues)
- **Documentation:** Check ARCHITECTURE.md and API.md first

---

## Additional Resources

- [SafeRoute Architecture](./ARCHITECTURE.md)
- [API Documentation](./API.md)
- [Testing Guide](./TESTING.md)
- [Security Guidelines](./SECURITY.md)

---

**Last Updated:** March 15, 2026  
**Version:** 1.0.0
