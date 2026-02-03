#!/bin/bash
# Development Script - Start all modules concurrently

set -e

echo "🚀 Starting Angular Module Federation Development Environment..."
echo ""
echo "Modules:"
echo "  - Shell (Host):        http://localhost:4200"
echo "  - Reg Reporting:       http://localhost:4201 (AG Grid v31)"
echo "  - Financial Reporting: http://localhost:4202 (AG Grid v30)"
echo "  - Expense Reporting:   http://localhost:4203 (AG Grid v31)"
echo "  - Tax Reporting:       http://localhost:4204 (AG Grid v29)"
echo "  - Control Tower:       http://localhost:4205 (AG Grid v31)"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install --legacy-peer-deps
fi

# Build shared library if not exists
if [ ! -d "dist/shared-lib" ]; then
  echo "📚 Building shared library..."
  npm run build:shared
fi

# Start all modules
echo "🔥 Starting all modules..."
npm run start:all
