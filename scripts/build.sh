#!/bin/bash
# Build script for Agentic RedTeam Radar
# Comprehensive build automation with security checks

set -euo pipefail

# Configuration
PROJECT_NAME="agentic-redteam-radar"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command_exists python3; then
        missing_tools+=("python3")
    fi
    
    if ! command_exists pip; then
        missing_tools+=("pip")
    fi
    
    if ! command_exists git; then
        missing_tools+=("git")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.10"
    
    if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
        log_error "Python $required_version or higher is required. Found: $python_version"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Clean previous builds
clean_build() {
    log_info "Cleaning previous builds..."
    
    rm -rf "$BUILD_DIR"
    rm -rf "$DIST_DIR"
    rm -rf "$PROJECT_ROOT"/*.egg-info
    rm -rf "$PROJECT_ROOT"/.pytest_cache
    rm -rf "$PROJECT_ROOT"/.mypy_cache
    rm -rf "$PROJECT_ROOT"/.ruff_cache
    rm -f "$PROJECT_ROOT"/.coverage
    rm -rf "$PROJECT_ROOT"/htmlcov
    
    find "$PROJECT_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "Build artifacts cleaned"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Upgrade pip and build tools
    python3 -m pip install --upgrade pip setuptools wheel build
    
    # Install project dependencies
    python3 -m pip install -e ".[dev,test,docs]"
    
    log_success "Dependencies installed"
}

# Run code quality checks
run_quality_checks() {
    log_info "Running code quality checks..."
    
    # Format check
    log_info "Checking code formatting..."
    if ! python3 -m black --check src tests; then
        log_error "Code formatting check failed. Run 'black src tests' to fix."
        return 1
    fi
    
    # Import sorting check
    log_info "Checking import sorting..."
    if ! python3 -m isort --check-only src tests; then
        log_error "Import sorting check failed. Run 'isort src tests' to fix."
        return 1
    fi
    
    # Linting
    log_info "Running linting checks..."
    if ! python3 -m flake8 src tests; then
        log_error "Linting check failed."
        return 1
    fi
    
    # Type checking
    log_info "Running type checking..."
    if ! python3 -m mypy src; then
        log_error "Type checking failed."
        return 1
    fi
    
    log_success "Code quality checks passed"
}

# Run security checks
run_security_checks() {
    log_info "Running security checks..."
    
    # Security scanning with bandit
    log_info "Running security scan with bandit..."
    if ! python3 -m bandit -r src/ -f json -o security-report.json; then
        log_warning "Security scan completed with warnings. Check security-report.json"
    fi
    
    # Dependency vulnerability scanning
    log_info "Scanning dependencies for vulnerabilities..."
    if command_exists pip-audit; then
        if ! python3 -m pip_audit --format=json --output=dependency-audit.json; then
            log_warning "Dependency audit completed with warnings. Check dependency-audit.json"
        fi
    else
        log_warning "pip-audit not available. Skipping dependency vulnerability scan."
    fi
    
    log_success "Security checks completed"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    # Unit tests
    log_info "Running unit tests..."
    python3 -m pytest tests/unit/ -v
    
    # Integration tests
    log_info "Running integration tests..."
    python3 -m pytest tests/integration/ -v
    
    # Coverage report
    log_info "Generating coverage report..."
    python3 -m pytest tests/ --cov=agentic_redteam --cov-report=html --cov-report=term-missing --cov-fail-under=80
    
    log_success "All tests passed"
}

# Build package
build_package() {
    log_info "Building package..."
    
    # Build source and wheel distributions
    python3 -m build
    
    # Check package integrity
    log_info "Checking package integrity..."
    if command_exists twine; then
        python3 -m twine check dist/*
    else
        log_warning "twine not available. Skipping package integrity check."
    fi
    
    log_success "Package built successfully"
}

# Build Docker image
build_docker() {
    log_info "Building Docker image..."
    
    if ! command_exists docker; then
        log_warning "Docker not available. Skipping Docker build."
        return 0
    fi
    
    # Get version from pyproject.toml
    version=$(grep 'version = ' pyproject.toml | cut -d'"' -f2)
    
    # Build production image
    docker build -t "$PROJECT_NAME:$version" -t "$PROJECT_NAME:latest" .
    
    # Build development image
    docker build --target development -t "$PROJECT_NAME:dev" .
    
    log_success "Docker images built successfully"
}

# Generate SBOM (Software Bill of Materials)
generate_sbom() {
    log_info "Generating Software Bill of Materials (SBOM)..."
    
    if command_exists cyclonedx-py; then
        cyclonedx-py -o sbom.json
        log_success "SBOM generated: sbom.json"
    else
        log_warning "cyclonedx-py not available. Skipping SBOM generation."
        log_info "Install with: pip install cyclonedx-bom"
    fi
}

# Create release artifacts
create_release_artifacts() {
    log_info "Creating release artifacts..."
    
    local artifacts_dir="$PROJECT_ROOT/artifacts"
    mkdir -p "$artifacts_dir"
    
    # Copy built packages
    cp -r "$DIST_DIR"/* "$artifacts_dir/"
    
    # Copy security reports
    if [ -f security-report.json ]; then
        cp security-report.json "$artifacts_dir/"
    fi
    
    if [ -f dependency-audit.json ]; then
        cp dependency-audit.json "$artifacts_dir/"
    fi
    
    # Copy SBOM
    if [ -f sbom.json ]; then
        cp sbom.json "$artifacts_dir/"
    fi
    
    # Create checksums
    cd "$artifacts_dir"
    find . -type f -name "*.whl" -o -name "*.tar.gz" | xargs sha256sum > checksums.sha256
    cd "$PROJECT_ROOT"
    
    log_success "Release artifacts created in $artifacts_dir"
}

# Print build summary
print_summary() {
    log_info "Build Summary:"
    echo "=================="
    
    if [ -d "$DIST_DIR" ]; then
        echo "📦 Built packages:"
        ls -la "$DIST_DIR"
        echo ""
    fi
    
    if command_exists docker; then
        echo "🐳 Docker images:"
        docker images "$PROJECT_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
        echo ""
    fi
    
    if [ -d artifacts ]; then
        echo "📋 Artifacts:"
        ls -la artifacts/
        echo ""
    fi
    
    log_success "Build completed successfully! 🎉"
}

# Main build function
main() {
    local skip_tests=false
    local skip_docker=false
    local skip_security=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                skip_tests=true
                shift
                ;;
            --skip-docker)
                skip_docker=true
                shift
                ;;
            --skip-security)
                skip_security=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-tests     Skip running tests"
                echo "  --skip-docker    Skip Docker image build"
                echo "  --skip-security  Skip security checks"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Starting build process for $PROJECT_NAME"
    log_info "Build options: tests=$([ "$skip_tests" = false ] && echo "enabled" || echo "disabled"), docker=$([ "$skip_docker" = false ] && echo "enabled" || echo "disabled"), security=$([ "$skip_security" = false ] && echo "enabled" || echo "disabled")"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run build steps
    check_prerequisites
    clean_build
    install_dependencies
    run_quality_checks
    
    if [ "$skip_security" = false ]; then
        run_security_checks
    fi
    
    if [ "$skip_tests" = false ]; then
        run_tests
    fi
    
    build_package
    
    if [ "$skip_docker" = false ]; then
        build_docker
    fi
    
    generate_sbom
    create_release_artifacts
    print_summary
}

# Error handling
set -e
trap 'log_error "Build failed at line $LINENO"' ERR

# Run main function
main "$@"