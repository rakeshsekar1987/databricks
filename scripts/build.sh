#!/bin/bash

# Build Script - Build all modules for production
# Usage: ./scripts/build.sh [module]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

# Check pnpm
check_pnpm() {
    if ! command -v pnpm &> /dev/null; then
        echo "Installing pnpm..."
        npm install -g pnpm
    fi
}

# Build function
build_module() {
    local module=$1
    print_message "Building $module..."
    pnpm --filter @platform/$module build
}

# Build all
build_all() {
    print_message "Building all modules for production..."
    
    # Build shared library first
    build_module "shared-library"
    
    # Build all apps in parallel
    pnpm run build
    
    print_message "Build complete!"
    
    echo ""
    echo -e "${BLUE}Build outputs:${NC}"
    echo "  - apps/shell/dist"
    echo "  - apps/reg-reporting/dist"
    echo "  - apps/financial-reporting/dist"
    echo "  - apps/expense-reporting/dist"
    echo "  - apps/tax-reporting/dist"
    echo "  - apps/control-tower/dist"
}

# Main
main() {
    cd "$(dirname "$0")/.."
    
    check_pnpm
    
    if [ ! -d "node_modules" ]; then
        print_message "Installing dependencies..."
        pnpm install
    fi

    if [ -n "$1" ]; then
        build_module "shared-library"
        build_module "$1"
    else
        build_all
    fi
}

main "$@"
