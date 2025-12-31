#!/bin/bash
###############################################################################
# Run Tests Script for alphafusion-issuetracker
#
# This script automatically:
#   1. Creates a virtual environment in ../venv/alphafusion-issuetracker-tests/ if it doesn't exist
#   2. Activates the virtual environment
#   3. Installs alphafusion-core package (from ../alphafusion-core)
#   4. Installs the alphafusion-issuetracker package and test dependencies
#   5. Runs the specified tests
#
# Usage:
#   ./run_tests.sh                    # Run all tests (unit + integration)
#   ./run_tests.sh unit               # Run only unit tests
#   ./run_tests.sh integration        # Run only integration tests
#   ./run_tests.sh unit/api           # Run unit tests for api
#   ./run_tests.sh --coverage         # Run tests with coverage report
#
# Virtual Environment:
#   The script creates and manages a virtual environment at: ../venv/alphafusion-issuetracker-tests/
#   This venv is automatically created on first run and reused on subsequent runs.
###############################################################################

# Note: We don't use 'set -e' because we need to handle errors manually
# for commands that may fail intentionally (like checking if pytest exists)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
ROOT_DIR="$( cd "$PROJECT_ROOT/.." && pwd )"

# Default options
TEST_PATH=""
COVERAGE=false
VERBOSE="-v"
COVERAGE_REPORT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --no-verbose|-q)
            VERBOSE=""
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [TEST_PATH]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c      Generate coverage report"
            echo "  --no-verbose, -q    Run tests quietly"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Run all tests (unit + integration)"
            echo "  $0 unit                      # Run only unit tests"
            echo "  $0 integration               # Run only integration tests"
            echo "  $0 unit/api                  # Run unit tests for api"
            echo "  $0 --coverage unit           # Run unit tests with coverage"
            exit 0
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

# Setup virtual environment at root level
VENV_DIR="$ROOT_DIR/venv/alphafusion-issuetracker-tests"
VENV_ACTIVATE="$VENV_DIR/bin/activate"

# Function to setup virtual environment
setup_venv() {
    echo -e "${BLUE}Setting up virtual environment...${NC}"
    
    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: python3 is not installed${NC}"
        echo "Please install Python 3.9 or higher"
        exit 1
    fi
    
    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to create virtual environment${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✓ Virtual environment already exists${NC}"
    fi
    
    # Activate virtual environment
    echo -e "${BLUE}Activating virtual environment...${NC}"
    source "$VENV_ACTIVATE"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to activate virtual environment${NC}"
        exit 1
    fi
    
    # Upgrade pip
    echo -e "${BLUE}Upgrading pip...${NC}"
    pip install --quiet --upgrade pip setuptools wheel > /dev/null 2>&1
    
    # Install alphafusion-core first (required dependency)
    CORE_DIR="$ROOT_DIR/alphafusion-core"
    if [ -d "$CORE_DIR" ] && [ -f "$CORE_DIR/pyproject.toml" ]; then
        echo -e "${BLUE}Installing alphafusion-core package...${NC}"
        pip install --quiet --upgrade -e "$CORE_DIR" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}Warning: Failed to install alphafusion-core, continuing...${NC}"
        else
            echo -e "${GREEN}✓ alphafusion-core installed${NC}"
        fi
    else
        echo -e "${YELLOW}Warning: alphafusion-core not found at $CORE_DIR${NC}"
        echo -e "${YELLOW}         Tests may fail if alphafusion-core is not available${NC}"
    fi
    
    # Install alphafusion-issuetracker package in editable mode
    echo -e "${BLUE}Installing alphafusion-issuetracker package...${NC}"
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        pip install --quiet --upgrade -e "$PROJECT_ROOT" > /dev/null 2>&1
        INSTALL_EXIT_CODE=$?
        if [ $INSTALL_EXIT_CODE -ne 0 ]; then
            echo -e "${YELLOW}Warning: Package installation had issues, continuing...${NC}"
        fi
    fi
    
    # Install test dependencies
    echo -e "${BLUE}Installing test dependencies...${NC}"
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        pip install --quiet --upgrade -e "$PROJECT_ROOT[dev]" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            # Fallback: install test dependencies separately
            pip install --quiet --upgrade pytest pytest-cov pytest-mock > /dev/null 2>&1
            if [ $? -ne 0 ]; then
                echo -e "${RED}Error: Failed to install test dependencies${NC}"
                exit 1
            fi
        fi
    else
        pip install --quiet --upgrade pytest pytest-cov pytest-mock > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to install test dependencies${NC}"
            exit 1
        fi
    fi
    
    # Install additional dependencies from requirements.txt if it exists
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        echo -e "${BLUE}Installing additional dependencies from requirements.txt...${NC}"
        pip install --quiet --upgrade -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1
    fi
    
    # Check if pytest is now available
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}Error: pytest is still not available after installation${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Test dependencies installed${NC}"
    echo ""
}

# Setup venv if needed
if [ ! -d "$VENV_DIR" ]; then
    # Venv doesn't exist, create it
    setup_venv
elif [ "$VIRTUAL_ENV" != "$VENV_DIR" ]; then
    # Venv exists but not activated, activate it and check dependencies
    source "$VENV_ACTIVATE"
    if ! command -v pytest &> /dev/null; then
        echo -e "${BLUE}Installing test dependencies...${NC}"
        # Install alphafusion-core if available
        CORE_DIR="$ROOT_DIR/alphafusion-core"
        if [ -d "$CORE_DIR" ] && [ -f "$CORE_DIR/pyproject.toml" ]; then
            pip install --quiet --upgrade -e "$CORE_DIR" > /dev/null 2>&1
        fi
        # Install issuetracker package
        if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
            pip install --quiet --upgrade -e "$PROJECT_ROOT[dev]" > /dev/null 2>&1 || pip install --quiet --upgrade pytest pytest-cov pytest-mock
        else
            pip install --quiet --upgrade pytest pytest-cov pytest-mock
        fi
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to install test dependencies${NC}"
            exit 1
        fi
    else
        # Pytest exists, but ensure package dependencies are up to date
        if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
            echo -e "${BLUE}Updating package dependencies...${NC}"
            CORE_DIR="$ROOT_DIR/alphafusion-core"
            if [ -d "$CORE_DIR" ] && [ -f "$CORE_DIR/pyproject.toml" ]; then
                pip install --quiet --upgrade -e "$CORE_DIR" > /dev/null 2>&1
            fi
            pip install --quiet --upgrade -e "$PROJECT_ROOT" > /dev/null 2>&1
        fi
    fi
else
    # Already in the test venv, just ensure pytest is installed
    if ! command -v pytest &> /dev/null; then
        echo -e "${BLUE}Installing test dependencies...${NC}"
        CORE_DIR="$ROOT_DIR/alphafusion-core"
        if [ -d "$CORE_DIR" ] && [ -f "$CORE_DIR/pyproject.toml" ]; then
            pip install --quiet --upgrade -e "$CORE_DIR" > /dev/null 2>&1
        fi
        if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
            pip install --quiet --upgrade -e "$PROJECT_ROOT[dev]" > /dev/null 2>&1 || pip install --quiet --upgrade pytest pytest-cov pytest-mock
        else
            pip install --quiet --upgrade pytest pytest-cov pytest-mock
        fi
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to install test dependencies${NC}"
            exit 1
        fi
    else
        # Pytest exists, but ensure package dependencies are up to date
        if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
            echo -e "${BLUE}Updating package dependencies...${NC}"
            CORE_DIR="$ROOT_DIR/alphafusion-core"
            if [ -d "$CORE_DIR" ] && [ -f "$CORE_DIR/pyproject.toml" ]; then
                pip install --quiet --upgrade -e "$CORE_DIR" > /dev/null 2>&1
            fi
            pip install --quiet --upgrade -e "$PROJECT_ROOT" > /dev/null 2>&1
        fi
    fi
fi

# Ensure venv is activated
if [ -f "$VENV_ACTIVATE" ] && [ "$VIRTUAL_ENV" != "$VENV_DIR" ]; then
    source "$VENV_ACTIVATE"
fi

# Print header
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  AlphaFusion IssueTracker Test Suite${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Determine test path
if [ -z "$TEST_PATH" ]; then
    # Run both unit and integration tests
    TEST_DIR="$SCRIPT_DIR"
    echo -e "${BLUE}Running all tests (unit + integration)${NC}"
elif [ "$TEST_PATH" = "unit" ]; then
    TEST_DIR="$SCRIPT_DIR/unit"
    echo -e "${BLUE}Running all unit tests${NC}"
elif [ "$TEST_PATH" = "integration" ]; then
    TEST_DIR="$SCRIPT_DIR/integration"
    echo -e "${BLUE}Running all integration tests${NC}"
else
    # Specific path within unit or integration
    if [ -d "$SCRIPT_DIR/$TEST_PATH" ]; then
        TEST_DIR="$SCRIPT_DIR/$TEST_PATH"
        echo -e "${BLUE}Running tests in: ${TEST_PATH}${NC}"
    elif [ -f "$SCRIPT_DIR/$TEST_PATH.py" ]; then
        TEST_DIR="$SCRIPT_DIR/$TEST_PATH.py"
        echo -e "${BLUE}Running test file: ${TEST_PATH}${NC}"
    elif [ -f "$SCRIPT_DIR/unit/$TEST_PATH.py" ]; then
        TEST_DIR="$SCRIPT_DIR/unit/$TEST_PATH.py"
        echo -e "${BLUE}Running test file: unit/${TEST_PATH}${NC}"
    elif [ -f "$SCRIPT_DIR/integration/$TEST_PATH.py" ]; then
        TEST_DIR="$SCRIPT_DIR/integration/$TEST_PATH.py"
        echo -e "${BLUE}Running test file: integration/${TEST_PATH}${NC}"
    else
        echo -e "${RED}Error: Test path not found: $TEST_PATH${NC}"
        exit 1
    fi
fi

echo ""

# Set PYTHONPATH to include project root (package-dir = "." for issuetracker)
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Create tests-output directory at root level if it doesn't exist
OUTPUT_DIR="$ROOT_DIR/tests-output/alphafusion-issuetracker"
mkdir -p "$OUTPUT_DIR"

# Convert TEST_DIR to relative path from SCRIPT_DIR for pytest
# This ensures pytest only discovers tests in the test directory
if [[ "$TEST_DIR" == "$SCRIPT_DIR"* ]]; then
    # Already relative to script dir
    REL_TEST_DIR="${TEST_DIR#$SCRIPT_DIR/}"
    if [ "$REL_TEST_DIR" = "$SCRIPT_DIR" ]; then
        REL_TEST_DIR="."
    fi
else
    REL_TEST_DIR="$TEST_DIR"
fi

# Build pytest command
PYTEST_CMD="pytest"
PYTEST_ARGS=(
    "$REL_TEST_DIR"
    "$VERBOSE"
    "--tb=short"
    "--color=yes"
    "--durations=10"
    "--disable-warnings"
    "--rootdir=$PROJECT_ROOT"
    "--ignore=venv"
)

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    if ! command -v pytest-cov &> /dev/null; then
        echo -e "${YELLOW}Warning: pytest-cov not installed, skipping coverage report${NC}"
        echo "Install with: pip install pytest-cov"
    else
        COVERAGE_HTML_DIR="$OUTPUT_DIR/coverage_html"
        COVERAGE_JSON="$OUTPUT_DIR/coverage.json"
        mkdir -p "$COVERAGE_HTML_DIR"
        
        PYTEST_ARGS+=(
            "--cov=apps"
            "--cov-report=term-missing:skip-covered"
            "--cov-report=html:$COVERAGE_HTML_DIR"
            "--cov-report=json:$COVERAGE_JSON"
        )
        COVERAGE_REPORT="Coverage report generated in: $COVERAGE_HTML_DIR/index.html"
    fi
fi

# Print test configuration
echo -e "${BLUE}Configuration:${NC}"
echo "  Project Root: $PROJECT_ROOT"
echo "  Test Directory: $TEST_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Python Path: $PYTHONPATH"
if [ "$COVERAGE" = true ]; then
    echo "  Coverage: Enabled"
fi
echo ""

# Run tests with timing
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Running Tests${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

START_TIME=$(date +%s)

# Run pytest
if $PYTEST_CMD "${PYTEST_ARGS[@]}"; then
    TEST_EXIT_CODE=0
else
    TEST_EXIT_CODE=$?
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Print separator
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Test Summary${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Print results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi

echo ""
echo -e "${BLUE}Execution Time:${NC} ${DURATION}s"
echo ""

# Print coverage info if available
if [ "$COVERAGE" = true ] && [ -n "$COVERAGE_REPORT" ]; then
    echo -e "${BLUE}Coverage:${NC}"
    echo "  $COVERAGE_REPORT"
    echo ""
fi

# Exit with test exit code
exit $TEST_EXIT_CODE

