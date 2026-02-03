#!/bin/bash

# =============================================================================
# Angular Module Federation POC - Single-Click Deployment Script
# =============================================================================
#
# This script builds and runs the complete micro-frontend architecture
# using Docker Compose with a single command.
#
# Usage:
#   ./run.sh          - Build and start all services
#   ./run.sh start    - Start existing containers
#   ./run.sh stop     - Stop all services
#   ./run.sh restart  - Restart all services
#   ./run.sh logs     - View logs
#   ./run.sh clean    - Remove all containers and images
#   ./run.sh status   - Show container status
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     Angular Module Federation POC - Docker Deployment         ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║  Shell (Host):         http://localhost:4200                  ║"
    echo "║  Reg Reporting:        http://localhost:4201  (AG Grid v31)   ║"
    echo "║  Financial Reporting:  http://localhost:4202  (AG Grid v30)   ║"
    echo "║  Expense Reporting:    http://localhost:4203  (AG Grid v31)   ║"
    echo "║  Tax Reporting:        http://localhost:4204  (AG Grid v29)   ║"
    echo "║  Control Tower:        http://localhost:4205  (AG Grid v31)   ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"
}

# Check if docker-compose is available
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}Error: docker-compose is not installed.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose is available${NC}"
}

# Build and start all services
build_and_start() {
    print_banner
    check_docker
    check_docker_compose
    
    echo -e "\n${YELLOW}Building and starting all services...${NC}"
    echo -e "${YELLOW}This may take several minutes on first run.${NC}\n"
    
    $COMPOSE_CMD up -d --build
    
    echo -e "\n${GREEN}✓ All services started successfully!${NC}"
    echo -e "\n${BLUE}Waiting for health checks...${NC}"
    
    sleep 10
    
    # Show status
    show_status
    
    echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Deployment Complete! Open http://localhost:4200 in browser  ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
}

# Start existing containers
start() {
    check_docker
    check_docker_compose
    echo -e "${YELLOW}Starting services...${NC}"
    $COMPOSE_CMD up -d
    echo -e "${GREEN}✓ Services started${NC}"
    show_status
}

# Stop all services
stop() {
    check_docker
    check_docker_compose
    echo -e "${YELLOW}Stopping all services...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}✓ All services stopped${NC}"
}

# Restart all services
restart() {
    check_docker
    check_docker_compose
    echo -e "${YELLOW}Restarting all services...${NC}"
    $COMPOSE_CMD restart
    echo -e "${GREEN}✓ All services restarted${NC}"
    show_status
}

# View logs
logs() {
    check_docker
    check_docker_compose
    echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    $COMPOSE_CMD logs -f
}

# Clean up everything
clean() {
    check_docker
    check_docker_compose
    echo -e "${YELLOW}Stopping and removing all containers, networks, and images...${NC}"
    $COMPOSE_CMD down --rmi all --volumes --remove-orphans
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Show container status
show_status() {
    check_docker
    check_docker_compose
    echo -e "\n${BLUE}Container Status:${NC}"
    echo "─────────────────────────────────────────────────────────────────"
    $COMPOSE_CMD ps
    echo "─────────────────────────────────────────────────────────────────"
}

# Show help
show_help() {
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  (none)    Build and start all services (default)"
    echo "  start     Start existing containers"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  logs      View container logs"
    echo "  status    Show container status"
    echo "  clean     Remove all containers and images"
    echo "  help      Show this help message"
}

# Main command handler
case "${1:-build}" in
    build)
        build_and_start
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        show_status
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
