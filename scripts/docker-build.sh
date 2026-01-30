#!/bin/bash

# Docker Build Script
# Usage: ./scripts/docker-build.sh [module]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[DOCKER]${NC} $1"
}

REGISTRY=${DOCKER_REGISTRY:-""}
VERSION=${VERSION:-"latest"}

# Build Docker image
build_image() {
    local module=$1
    local dockerfile=$2
    local tag="${REGISTRY}ui-platform/${module}:${VERSION}"
    
    print_message "Building Docker image: $tag"
    
    docker build \
        -f "$dockerfile" \
        -t "$tag" \
        --build-arg NODE_ENV=production \
        ${BUILD_ARGS:-} \
        .
    
    print_message "Built: $tag"
}

# Build all images
build_all() {
    print_message "Building all Docker images..."
    
    # Build shell
    build_image "shell" "infrastructure/docker/Dockerfile.shell"
    
    # Build remote modules
    for module in reg-reporting financial-reporting expense-reporting tax-reporting control-tower; do
        docker build \
            -f "infrastructure/docker/Dockerfile.module" \
            -t "${REGISTRY}ui-platform/${module}:${VERSION}" \
            --build-arg MODULE_NAME=$module \
            --build-arg NODE_ENV=production \
            .
        print_message "Built: ${REGISTRY}ui-platform/${module}:${VERSION}"
    done
    
    # Build module registry
    docker build \
        -f "infrastructure/module-registry/Dockerfile" \
        -t "${REGISTRY}ui-platform/module-registry:${VERSION}" \
        infrastructure/module-registry/
    
    print_message "All images built successfully!"
}

# Main
main() {
    cd "$(dirname "$0")/.."
    
    if [ -n "$1" ]; then
        case $1 in
            shell)
                build_image "shell" "infrastructure/docker/Dockerfile.shell"
                ;;
            registry)
                docker build \
                    -f "infrastructure/module-registry/Dockerfile" \
                    -t "${REGISTRY}ui-platform/module-registry:${VERSION}" \
                    infrastructure/module-registry/
                ;;
            *)
                docker build \
                    -f "infrastructure/docker/Dockerfile.module" \
                    -t "${REGISTRY}ui-platform/$1:${VERSION}" \
                    --build-arg MODULE_NAME=$1 \
                    --build-arg NODE_ENV=production \
                    .
                ;;
        esac
    else
        build_all
    fi
}

main "$@"
