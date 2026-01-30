# UI/UX Module Federation Architecture

## Overview

This document describes the Module Federation architecture for the UI/UX platform, enabling independent development, deployment, and versioning of micro-frontends.

## Problem Statement

### Current Challenges
1. **Tight Coupling**: All UI modules are in a single codebase requiring coordinated releases
2. **Deployment Bottlenecks**: Teams wait for code merges before deploying
3. **Version Conflicts**: Cannot run different versions of dependencies (e.g., AG Grid) across modules
4. **Slow CI/CD**: Full builds required even for small changes

### Solution: Module Federation

Module Federation (Webpack 5) allows loading separately compiled and deployed code at runtime, enabling:
- Independent deployments per module
- Different dependency versions per module
- Parallel team development
- Shared code optimization

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Shell Application                               │
│                         (Main UI Container/Host)                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Module Federation Runtime                        ││
│  │  - Dynamic Remote Loading                                               ││
│  │  - Shared Dependencies Management                                       ││
│  │  - Version Negotiation                                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
         │              │              │              │              │
         ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│     Reg     │ │  Financial  │ │   Expense   │ │     Tax     │ │   Control   │
│  Reporting  │ │  Reporting  │ │  Reporting  │ │  Reporting  │ │    Tower    │
│   Module    │ │   Module    │ │   Module    │ │   Module    │ │   Module    │
│             │ │             │ │             │ │             │ │             │
│ AG Grid v31 │ │ AG Grid v30 │ │ AG Grid v31 │ │ AG Grid v29 │ │ AG Grid v31 │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
         │              │              │              │              │
         └──────────────┴──────────────┼──────────────┴──────────────┘
                                       ▼
                          ┌─────────────────────────┐
                          │    Shared Library       │
                          │  - Common Components    │
                          │  - Utils & Helpers      │
                          │  - Design System        │
                          │  - Auth Context         │
                          └─────────────────────────┘
```

## Module Structure

### 1. Shell Application (Host)
The main container application that:
- Provides global navigation and layout
- Manages authentication/authorization
- Dynamically loads remote modules
- Handles routing between modules

### 2. Remote Modules
Each business domain is a separate federated module:

| Module | Description | Repository | Independent AG Grid |
|--------|-------------|------------|---------------------|
| Reg Reporting | Regulatory reporting features | `reg-reporting-ui` | ✅ |
| Financial Reporting | Financial statements & reports | `financial-reporting-ui` | ✅ |
| Expense Reporting | Expense management | `expense-reporting-ui` | ✅ |
| Tax Reporting | Tax calculations & filing | `tax-reporting-ui` | ✅ |
| Control Tower | Dashboard & monitoring | `control-tower-ui` | ✅ |

### 3. Shared Library
Common code shared across all modules:
- UI Component Library (Design System)
- Authentication utilities
- API clients
- Common hooks and utilities

## AG Grid Versioning Strategy

### Problem
Different modules need different AG Grid versions due to:
- Feature requirements
- Migration timelines
- Stability concerns

### Solution: Isolated AG Grid Instances

```javascript
// Each module declares its own AG Grid version
// webpack.config.js for Tax Reporting (needs v29)
new ModuleFederationPlugin({
  name: 'taxReporting',
  shared: {
    'ag-grid-community': {
      singleton: false, // Allow multiple versions
      requiredVersion: '^29.0.0'
    },
    'ag-grid-react': {
      singleton: false,
      requiredVersion: '^29.0.0'
    }
  }
})
```

### Version Isolation Pattern
```
┌─────────────────────────────────────────────────────────────┐
│                    Shell Application                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  Tax Module    │  │ Finance Module │  │ Control Tower  │ │
│  │  ┌──────────┐  │  │  ┌──────────┐  │  │  ┌──────────┐  │ │
│  │  │AG Grid   │  │  │  │AG Grid   │  │  │  │AG Grid   │  │ │
│  │  │v29.x     │  │  │  │v30.x     │  │  │  │v31.x     │  │ │
│  │  └──────────┘  │  │  └──────────┘  │  │  └──────────┘  │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Build & Deployment Flow

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│   Git Push   │────▶│  Change Detection │────▶│ Selective    │
│   (Module)   │     │  (CI Pipeline)    │     │ Build        │
└──────────────┘     └───────────────────┘     └──────────────┘
                                                      │
                                                      ▼
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│  Deployment  │◀────│  JFrog Artifact   │◀────│  Package &   │
│  (CDN/K8s)   │     │  Repository       │     │  Version     │
└──────────────┘     └───────────────────┘     └──────────────┘
```

### Independent Deployment Process

1. **Developer pushes to module repo** (e.g., `tax-reporting-ui`)
2. **CI detects changes** and triggers module-specific build
3. **Module is built and packaged** with unique version
4. **Artifact published to JFrog** with semantic versioning
5. **Shell application updated** to reference new module version (or uses dynamic discovery)
6. **Module deployed to CDN/K8s** independently

## Runtime Module Discovery

### Static Configuration
```json
{
  "modules": {
    "regReporting": "https://cdn.example.com/reg-reporting/v2.1.0/remoteEntry.js",
    "financialReporting": "https://cdn.example.com/financial-reporting/v1.5.0/remoteEntry.js",
    "taxReporting": "https://cdn.example.com/tax-reporting/v3.0.0/remoteEntry.js"
  }
}
```

### Dynamic Discovery (Recommended)
```javascript
// Runtime module discovery from configuration service
const moduleRegistry = await fetch('/api/module-registry');
const { modules } = await moduleRegistry.json();

// Load modules dynamically
const TaxReporting = await loadRemote(modules.taxReporting, './TaxApp');
```

## Directory Structure

```
ui-module-federation/
├── apps/
│   ├── shell/                    # Host application
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── bootstrap.tsx
│   │   │   ├── components/
│   │   │   │   ├── Layout.tsx
│   │   │   │   ├── Navigation.tsx
│   │   │   │   └── ModuleLoader.tsx
│   │   │   └── routes/
│   │   ├── webpack.config.js
│   │   └── package.json
│   │
│   ├── reg-reporting/            # Remote module
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── bootstrap.tsx
│   │   │   └── components/
│   │   ├── webpack.config.js
│   │   └── package.json
│   │
│   ├── financial-reporting/      # Remote module
│   ├── expense-reporting/        # Remote module
│   ├── tax-reporting/            # Remote module
│   └── control-tower/            # Remote module
│
├── packages/
│   └── shared-library/           # Shared components & utils
│       ├── src/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── utils/
│       │   └── index.ts
│       └── package.json
│
├── infrastructure/
│   ├── docker/
│   ├── kubernetes/
│   └── terraform/
│
├── .github/
│   └── workflows/
│       ├── shell.yml
│       ├── reg-reporting.yml
│       ├── financial-reporting.yml
│       ├── expense-reporting.yml
│       ├── tax-reporting.yml
│       └── control-tower.yml
│
├── package.json                  # Workspace root
├── pnpm-workspace.yaml
└── turbo.json                    # Turborepo config
```

## Benefits

| Benefit | Description |
|---------|-------------|
| **Independent Deployments** | Each module can be deployed without affecting others |
| **Parallel Development** | Teams work independently without merge conflicts |
| **Version Flexibility** | Different AG Grid versions per module |
| **Faster Builds** | Only changed modules are rebuilt |
| **Smaller Bundles** | Shared dependencies loaded once |
| **A/B Testing** | Easy to deploy different versions |
| **Rollback** | Individual module rollback capability |

## Migration Strategy

### Phase 1: Setup Infrastructure
- Create monorepo structure
- Configure Module Federation
- Set up CI/CD pipelines

### Phase 2: Extract Shared Library
- Identify common components
- Create shared package
- Configure sharing in Module Federation

### Phase 3: Migrate Modules (One at a Time)
1. Reg Reporting → Federated Module
2. Financial Reporting → Federated Module
3. Expense Reporting → Federated Module
4. Tax Reporting → Federated Module
5. Control Tower → Federated Module

### Phase 4: Optimize
- Performance tuning
- Shared dependency optimization
- Monitoring and observability
