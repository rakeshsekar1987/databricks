#!/bin/bash
# Build Script - Build all modules for production

set -e

echo "🔨 Building Angular Module Federation Platform..."
echo ""

# Parse arguments
MODULE=$1

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm ci --legacy-peer-deps
fi

# Build shared library first
echo "📚 Building shared library..."
npm run build:shared

if [ -z "$MODULE" ]; then
  # Build all modules
  echo "🏗️ Building all modules..."
  npm run build:shell
  npm run build:reg-reporting
  npm run build:financial-reporting
  npm run build:expense-reporting
  npm run build:tax-reporting
  npm run build:control-tower
else
  # Build specific module
  echo "🏗️ Building $MODULE..."
  npm run build:$MODULE
fi

echo ""
echo "✅ Build complete! Output in ./dist/"
