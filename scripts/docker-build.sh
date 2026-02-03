#!/bin/bash
# Docker Build Script - Build all Docker images

set -e

REGISTRY=${REGISTRY:-"ghcr.io/your-org"}
VERSION=${VERSION:-"latest"}

echo "🐳 Building Docker images..."
echo "Registry: $REGISTRY"
echo "Version: $VERSION"
echo ""

# Build shell
echo "Building shell..."
docker build -f infrastructure/docker/Dockerfile.shell \
  -t $REGISTRY/shell:$VERSION \
  -t $REGISTRY/shell:latest \
  .

# Build modules
MODULES=("reg-reporting" "financial-reporting" "expense-reporting" "tax-reporting" "control-tower")

for MODULE in "${MODULES[@]}"; do
  echo "Building $MODULE..."
  docker build -f infrastructure/docker/Dockerfile.module \
    --build-arg MODULE_NAME=$MODULE \
    -t $REGISTRY/$MODULE:$VERSION \
    -t $REGISTRY/$MODULE:latest \
    .
done

echo ""
echo "✅ Docker images built successfully!"
echo ""
echo "Images created:"
docker images | grep $REGISTRY | head -20
