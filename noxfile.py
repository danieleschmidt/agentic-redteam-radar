"""
Nox configuration for advanced testing and quality assurance.
Provides comprehensive test automation across Python versions and environments.
"""

import nox

# Supported Python versions for this project
PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]
LINT_TOOLS = ["black", "isort", "flake8", "mypy"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run the test suite with coverage."""
    session.install("-e", ".[test]")
    session.run(
        "pytest",
        "--cov=agentic_redteam",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=80",
        *session.posargs,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )


@nox.session(python=PYTHON_VERSIONS)
def integration_tests(session):
    """Run integration tests against live services."""
    session.install("-e", ".[test]")
    session.run("pytest", "-m", "integration", *session.posargs)


@nox.session(python="3.11")
def performance_tests(session):
    """Run performance and load tests."""
    session.install("-e", ".[test]", "pytest-benchmark", "locust")
    session.run("pytest", "-m", "performance", "--benchmark-only", *session.posargs)


@nox.session(python="3.11")
def security_tests(session):
    """Run security-focused tests and scans."""
    session.install("-e", ".[test]", "bandit[toml]", "pip-audit", "safety")
    session.run("bandit", "-r", "src/", "-f", "json", "-o", "bandit-report.json")
    session.run("pip-audit", "--format=json", "--output=pip-audit-report.json")
    session.run("safety", "check", "--json", "--output", "safety-report.json")
    session.run("pytest", "-m", "security", *session.posargs)


@nox.session(python="3.11")
def mutation_tests(session):
    """Run mutation testing to assess test quality."""
    session.install("-e", ".[test]", "mutmut")
    session.run("mutmut", "run", "--paths-to-mutate=src/agentic_redteam")


@nox.session(python="3.11")
def lint(session):
    """Run linting and formatting checks."""
    session.install(*LINT_TOOLS, "flake8-docstrings", "flake8-bugbear")
    session.run("black", "--check", ".")
    session.run("isort", "--check-only", ".")
    session.run("flake8", "src/", "tests/")
    session.run("mypy", "src/")


@nox.session(python="3.11")
def format_code(session):
    """Format code using black and isort."""
    session.install("black", "isort")
    session.run("black", ".")
    session.run("isort", ".")


@nox.session(python="3.11")
def docs(session):
    """Build documentation."""
    session.install("-e", ".[docs]")
    session.run("mkdocs", "build", "--clean")


@nox.session(python="3.11")
def docs_serve(session):
    """Serve documentation locally."""
    session.install("-e", ".[docs]")
    session.run("mkdocs", "serve")


@nox.session(python="3.11")
def type_check(session):
    """Run comprehensive type checking."""
    session.install("mypy", "types-all")
    session.run("mypy", "src/", "--strict", "--show-error-codes")


@nox.session(python="3.11")
def coverage_report(session):
    """Generate comprehensive coverage reports."""
    session.install("coverage[toml]")
    session.run("coverage", "combine")
    session.run("coverage", "report", "--show-missing")
    session.run("coverage", "html")
    session.run("coverage", "xml")


@nox.session(python="3.11")
def build(session):
    """Build the package."""
    session.install("build", "twine")
    session.run("python", "-m", "build")
    session.run("twine", "check", "dist/*")


@nox.session(python="3.11")
def pre_commit(session):
    """Run pre-commit hooks on all files."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session(python="3.11")
def audit(session):
    """Run comprehensive security and dependency audits."""
    session.install("pip-audit", "safety", "bandit[toml]")
    session.run("pip-audit")
    session.run("safety", "check")
    session.run("bandit", "-r", "src/")


@nox.session(python="3.11")
def benchmark(session):
    """Run benchmarking tests."""
    session.install("-e", ".[test]", "pytest-benchmark")
    session.run("pytest", "tests/performance/", "--benchmark-sort=mean")


# Cleanup session
@nox.session
def clean(session):
    """Clean up build artifacts and cache."""
    import shutil
    import pathlib
    
    patterns = [
        ".coverage*",
        "htmlcov/",
        ".pytest_cache/",
        ".mypy_cache/", 
        "__pycache__/",
        "build/",
        "dist/",
        "*.egg-info/",
        ".nox/",
        "site/",
        "*.pyc",
        "*.pyo",
    ]
    
    for pattern in patterns:
        for path in pathlib.Path(".").rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
    
    session.log("Cleaned up build artifacts and cache files")