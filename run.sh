#!/bin/bash

# =============================================================================
# Angular Module Federation POC - Single-Click Deployment Script
# =============================================================================
#
# Usage:
#   ./run.sh          - Build and start all services
#   ./run.sh stop     - Stop all services
#   ./run.sh logs     - View logs
#   ./run.sh clean    - Remove all containers and images
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "     Angular Module Federation POC - Docker Deployment      "
    echo "============================================================"
    echo ""
    echo "  Shell (Host):         http://localhost:4200"
    echo "  Reg Reporting:        http://localhost:4201"
    echo "  Financial Reporting:  http://localhost:4202"
    echo "  Expense Reporting:    http://localhost:4203"
    echo "  Tax Reporting:        http://localhost:4204"
    echo "  Control Tower:        http://localhost:4205"
    echo ""
    echo "============================================================"
    echo -e "${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
}

# Determine docker-compose command
get_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo -e "${RED}Error: docker-compose is not installed.${NC}"
        exit 1
    fi
}

# Build and start
build_and_start() {
    print_banner
    check_docker
    COMPOSE_CMD=$(get_compose_cmd)
    
    echo -e "${YELLOW}Building and starting all services...${NC}"
    echo -e "${YELLOW}This may take several minutes on first run.${NC}"
    echo ""
    
    $COMPOSE_CMD up -d --build
    
    echo ""
    echo -e "${GREEN}All services started!${NC}"
    echo ""
    $COMPOSE_CMD ps
    echo ""
    echo -e "${GREEN}Open http://localhost:4200 in your browser${NC}"
}

# Stop
stop() {
    check_docker
    COMPOSE_CMD=$(get_compose_cmd)
    echo -e "${YELLOW}Stopping all services...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}All services stopped.${NC}"
}

# Logs
logs() {
    check_docker
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD logs -f
}

# Clean
clean() {
    check_docker
    COMPOSE_CMD=$(get_compose_cmd)
    echo -e "${YELLOW}Removing all containers and images...${NC}"
    $COMPOSE_CMD down --rmi all --volumes --remove-orphans
    echo -e "${GREEN}Cleanup complete.${NC}"
}

# Status
status() {
    check_docker
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD ps
}

# Help
show_help() {
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  (none)    Build and start all services"
    echo "  stop      Stop all services"
    echo "  logs      View container logs"
    echo "  status    Show container status"
    echo "  clean     Remove all containers and images"
    echo "  help      Show this help"
}

# Main
case "${1:-}" in
    ""|build|start)
        build_and_start
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
