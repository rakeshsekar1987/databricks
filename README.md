# UI Platform - Module Federation Architecture

A modern micro-frontend architecture using Webpack Module Federation, enabling independent development, deployment, and versioning of UI modules with support for different AG Grid versions per module.

## Overview

This platform solves the tight coupling problem by implementing Module Federation, allowing:

- **Independent Deployments**: Each module can be deployed without affecting others
- **Different AG Grid Versions**: Each service can run its own version of AG Grid
- **Parallel Development**: Teams work independently without blocking each other
- **Faster Builds**: Only changed modules are rebuilt

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Shell Application                               │
│                         (Main UI Container/Host)                            │
└─────────────────────────────────────────────────────────────────────────────┘
         │              │              │              │              │
         ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│     Reg     │ │  Financial  │ │   Expense   │ │     Tax     │ │   Control   │
│  Reporting  │ │  Reporting  │ │  Reporting  │ │  Reporting  │ │    Tower    │
│ AG Grid v31 │ │ AG Grid v30 │ │ AG Grid v31 │ │ AG Grid v29 │ │ AG Grid v31 │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## AG Grid Version Matrix

| Module | AG Grid Version | Purpose |
|--------|-----------------|---------|
| Reg Reporting | v31.0.0 | Latest features for regulatory compliance |
| Financial Reporting | v30.2.0 | Stable version with specific features |
| Expense Reporting | v31.0.0 | Latest features for expense tracking |
| Tax Reporting | v29.3.0 | Legacy compatibility for tax calculations |
| Control Tower | v31.0.0 | Dashboard and monitoring |

## Project Structure

```
ui-module-federation/
├── apps/
│   ├── shell/                    # Host application (port 3000)
│   ├── reg-reporting/            # Remote module (port 3001)
│   ├── financial-reporting/      # Remote module (port 3002)
│   ├── expense-reporting/        # Remote module (port 3003)
│   ├── tax-reporting/            # Remote module (port 3004)
│   └── control-tower/            # Remote module (port 3005)
├── packages/
│   └── shared-library/           # Shared components & utilities
├── infrastructure/
│   ├── docker/                   # Docker configurations
│   ├── kubernetes/               # K8s manifests
│   └── module-registry/          # Dynamic module discovery service
├── .github/
│   └── workflows/                # CI/CD pipelines
└── docs/
    └── ARCHITECTURE.md           # Detailed architecture documentation
```

## Quick Start

### Prerequisites

- Node.js >= 18.0.0
- pnpm >= 8.0.0

### Installation

```bash
# Install pnpm if not already installed
npm install -g pnpm

# Install dependencies
pnpm install

# Build shared library
pnpm build:shared
```

### Development

Run all modules in development mode:

```bash
# Start all modules (in separate terminals)
pnpm --filter @platform/shell dev          # http://localhost:3000
pnpm --filter @platform/reg-reporting dev  # http://localhost:3001
pnpm --filter @platform/financial-reporting dev  # http://localhost:3002
pnpm --filter @platform/expense-reporting dev    # http://localhost:3003
pnpm --filter @platform/tax-reporting dev       # http://localhost:3004
pnpm --filter @platform/control-tower dev       # http://localhost:3005
```

Or use Docker Compose:

```bash
cd infrastructure/docker
docker-compose up --build
```

### Building

```bash
# Build all
pnpm build

# Build specific module
pnpm build:shell
pnpm build:reg-reporting
pnpm build:tax-reporting
```

## Module Federation Configuration

### Shell (Host) Application

The shell application loads remote modules dynamically:

```javascript
// webpack.config.js
new ModuleFederationPlugin({
  name: 'shell',
  remotes: {
    regReporting: 'regReporting@http://localhost:3001/remoteEntry.js',
    taxReporting: 'taxReporting@http://localhost:3004/remoteEntry.js',
    // ... other modules
  },
  shared: {
    react: { singleton: true },
    'react-dom': { singleton: true },
    // AG Grid is NOT shared - each module has its own version
  },
})
```

### Remote Module Configuration

Each module exposes components and manages its own dependencies:

```javascript
// webpack.config.js for tax-reporting (AG Grid v29)
new ModuleFederationPlugin({
  name: 'taxReporting',
  filename: 'remoteEntry.js',
  exposes: {
    './App': './src/App',
  },
  shared: {
    react: { singleton: true },
    'ag-grid-community': {
      singleton: false,  // Allow different versions
      requiredVersion: '^29.3.0',
    },
  },
})
```

## Key Features

### 1. Independent Module Versioning

Each module has its own `package.json` with independent dependency versions:

```json
// apps/tax-reporting/package.json
{
  "dependencies": {
    "ag-grid-community": "^29.3.0"  // v29 for Tax
  }
}

// apps/reg-reporting/package.json
{
  "dependencies": {
    "ag-grid-community": "^31.0.0"  // v31 for Reg
  }
}
```

### 2. Dynamic Module Discovery

The Module Registry Service provides runtime module discovery:

```javascript
// Fetch module configuration at runtime
const manifest = await fetch('/api/module-manifest');
const { modules } = await manifest.json();

// Load module dynamically
const TaxReporting = await loadRemote(modules.taxReporting, './App');
```

### 3. Shared Library

Common components and utilities are shared across all modules:

```typescript
// Import shared components
import { Button, Card, Badge } from '@platform/shared-library';

// Import shared hooks
import { useAsync, useDebounce } from '@platform/shared-library/hooks';

// Import shared utilities
import { formatCurrency, loadRemoteModule } from '@platform/shared-library/utils';
```

## CI/CD Pipeline

Each module has its own CI/CD pipeline triggered by path-specific changes:

```yaml
# .github/workflows/tax-reporting.yml
on:
  push:
    paths:
      - 'apps/tax-reporting/**'
      - 'packages/shared-library/**'
```

### Pipeline Stages

1. **Build**: Compile and bundle the module
2. **Test**: Run unit tests and linting
3. **Publish**: Upload artifacts to JFrog
4. **Deploy**: Deploy to CDN/Kubernetes

## Deployment Options

### 1. CDN Deployment

Modules are deployed as static assets to a CDN:

```
https://cdn.example.com/
├── shell/
│   └── v1.0.0/
├── reg-reporting/
│   └── v2.1.0/
├── tax-reporting/
│   └── v3.0.1/
```

### 2. Kubernetes Deployment

Each module runs as an independent service:

```bash
kubectl apply -k infrastructure/kubernetes/
```

### 3. Docker Compose

For local development or simple deployments:

```bash
docker-compose up --build
```

## Module Registry API

The Module Registry Service provides endpoints for module discovery:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/module-manifest` | GET | Get all modules configuration |
| `/api/modules/{name}` | GET | Get specific module configuration |
| `/api/modules/{name}` | POST | Update module configuration |
| `/api/ag-grid-versions` | GET | Get AG Grid versions summary |

## Benefits

| Benefit | Description |
|---------|-------------|
| **Independent Deployments** | Deploy modules without affecting others |
| **Parallel Development** | Teams work independently without merge conflicts |
| **Version Flexibility** | Different AG Grid versions per module |
| **Faster Builds** | Only changed modules are rebuilt |
| **Smaller Bundles** | Shared dependencies loaded once |
| **A/B Testing** | Easy to deploy different versions |
| **Rollback** | Individual module rollback capability |

## Migration Guide

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed migration strategy from monolithic to Module Federation architecture.

## License

MIT
