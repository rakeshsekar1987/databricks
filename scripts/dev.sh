#!/bin/bash

# Development Script - Start all modules in development mode
# Usage: ./scripts/dev.sh [module]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${GREEN}[DEV]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if pnpm is installed
check_pnpm() {
    if ! command -v pnpm &> /dev/null; then
        print_error "pnpm is not installed. Installing..."
        npm install -g pnpm
    fi
}

# Install dependencies if needed
install_deps() {
    if [ ! -d "node_modules" ]; then
        print_message "Installing dependencies..."
        pnpm install
    fi
}

# Build shared library
build_shared() {
    print_message "Building shared library..."
    pnpm --filter @platform/shared-library build
}

# Start a specific module
start_module() {
    local module=$1
    local port=$2
    print_message "Starting $module on port $port..."
    pnpm --filter @platform/$module dev &
}

# Start all modules
start_all() {
    print_message "Starting all modules in development mode..."
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║            Module Federation - Development Mode            ║${NC}"
    echo -e "${BLUE}╠════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║  Shell (Host):        http://localhost:3000                ║${NC}"
    echo -e "${BLUE}║  Reg Reporting:       http://localhost:3001 (AG Grid v31)  ║${NC}"
    echo -e "${BLUE}║  Financial Reporting: http://localhost:3002 (AG Grid v30)  ║${NC}"
    echo -e "${BLUE}║  Expense Reporting:   http://localhost:3003 (AG Grid v31)  ║${NC}"
    echo -e "${BLUE}║  Tax Reporting:       http://localhost:3004 (AG Grid v29)  ║${NC}"
    echo -e "${BLUE}║  Control Tower:       http://localhost:3005 (AG Grid v31)  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Start all remote modules first
    start_module "reg-reporting" 3001
    sleep 1
    start_module "financial-reporting" 3002
    sleep 1
    start_module "expense-reporting" 3003
    sleep 1
    start_module "tax-reporting" 3004
    sleep 1
    start_module "control-tower" 3005
    sleep 2

    # Start shell last (it depends on remotes)
    start_module "shell" 3000

    print_message "All modules started. Press Ctrl+C to stop."
    
    # Wait for all background processes
    wait
}

# Main
main() {
    cd "$(dirname "$0")/.."
    
    check_pnpm
    install_deps
    build_shared

    if [ -n "$1" ]; then
        # Start specific module
        case $1 in
            shell)
                start_module "shell" 3000
                ;;
            reg|reg-reporting)
                start_module "reg-reporting" 3001
                ;;
            financial|financial-reporting)
                start_module "financial-reporting" 3002
                ;;
            expense|expense-reporting)
                start_module "expense-reporting" 3003
                ;;
            tax|tax-reporting)
                start_module "tax-reporting" 3004
                ;;
            control|control-tower)
                start_module "control-tower" 3005
                ;;
            *)
                print_error "Unknown module: $1"
                echo "Available modules: shell, reg-reporting, financial-reporting, expense-reporting, tax-reporting, control-tower"
                exit 1
                ;;
        esac
        wait
    else
        start_all
    fi
}

main "$@"
