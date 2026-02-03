# Angular Module Federation Architecture

## Overview

This document describes the Angular Module Federation architecture for the UI/UX platform, enabling independent development, deployment, and versioning of micro-frontends with Motif Design System integration.

## Problem Statement

### Current Challenges
1. **Tight Coupling**: All UI modules in a single codebase requiring coordinated releases
2. **Deployment Bottlenecks**: Teams wait for code merges before deploying
3. **Version Conflicts**: Cannot run different versions of AG Grid across modules
4. **Slow CI/CD**: Full builds required even for small changes

### Solution: Angular Module Federation

Module Federation (Webpack 5) with Angular enables:
- Independent deployments per module
- Different AG Grid versions per module (v29, v30, v31)
- Parallel team development
- Shared Motif components optimization

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Shell Application                               │
│                         (Angular 17 Host Container)                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Module Federation Runtime                        ││
│  │  - @angular-architects/module-federation                               ││
│  │  - Dynamic Remote Loading                                              ││
│  │  - Shared Dependencies (Angular, Motif)                                ││
│  │  - Version Negotiation                                                 ││
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
              ┌───────────────────────────────────────────────────┐
              │              Shared Libraries                      │
              │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
              │  │   @shared   │  │  @mfs/motif │  │   Angular   ││
              │  │    -lib     │  │  (Singleton)│  │  (Singleton)││
              │  └─────────────┘  └─────────────┘  └─────────────┘│
              └───────────────────────────────────────────────────┘
```

## Module Structure

### 1. Shell Application (Host)

The main container application responsible for:
- Global navigation and layout (Header, Sidebar, Footer)
- Authentication/authorization context
- Dynamic remote module loading via routes
- Error boundaries and fallback UI
- Motif theme configuration

### 2. Remote Modules

Each business domain is a separate federated module:

| Module | AG Grid | Port | Responsibility |
|--------|---------|------|----------------|
| Reg Reporting | v31 | 4201 | Regulatory compliance |
| Financial Reporting | v30 | 4202 | Financial statements |
| Expense Reporting | v31 | 4203 | Expense management |
| Tax Reporting | v29 | 4204 | Tax calculations |
| Control Tower | v31 | 4205 | Dashboard & monitoring |

### 3. Shared Library

Common code shared as singleton across modules:
- Motif-styled UI components (Button, Card, Alert, etc.)
- Common services (API, Storage, Notification)
- TypeScript interfaces and models
- Utility functions (formatters, validators)

## AG Grid Version Isolation

### Strategy

Each module bundles its own AG Grid version by:

1. **Not sharing AG Grid as singleton** in webpack config
2. **Each module declares its version** in package.json
3. **Webpack bundles AG Grid** with the module

```javascript
// projects/tax-reporting/webpack.config.js
shared: {
  'ag-grid-community': {
    singleton: false,  // Critical: allows different versions
    requiredVersion: '^29.3.0'
  }
}
```

### Version Matrix

| Module | AG Grid Version | Reason |
|--------|----------------|--------|
| Tax Reporting | v29.3.0 | Legacy compatibility |
| Financial Reporting | v30.2.0 | Specific feature requirements |
| Others | v31.0.0 | Latest features |

## Build & Deployment Architecture

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│   Git Push   │────▶│  Path-based CI    │────▶│   Selective  │
│   (Module)   │     │  Detection        │     │   Build      │
└──────────────┘     └───────────────────┘     └──────────────┘
                                                      │
                                                      ▼
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│  Kubernetes  │◀────│  Container        │◀────│   Docker     │
│  Deployment  │     │  Registry         │     │   Build      │
└──────────────┘     └───────────────────┘     └──────────────┘
```

### Independent Deployment Flow

1. Developer pushes to module directory
2. CI detects changed paths, triggers module-specific build
3. Module compiled with standalone AG Grid version
4. Docker image built and pushed to registry
5. Kubernetes deploys module independently
6. Shell loads updated remote at runtime

## Motif Design System Integration

### Shared as Singleton

Motif library is shared across all modules:

```javascript
shared: {
  '@mfs/motif': {
    singleton: true,
    strictVersion: false
  }
}
```

### Theme Configuration

Global CSS variables in shell's `styles.scss`:

```scss
:root {
  --motif-primary: #1976d2;
  --motif-secondary: #424242;
  --motif-success: #4caf50;
  --motif-error: #f44336;
  // ... more design tokens
}
```

## Best Practices

### Angular Patterns
- **Standalone Components**: No NgModules, cleaner imports
- **Signals**: Reactive state without complex RxJS
- **OnPush Change Detection**: Better performance
- **Lazy Loading**: Routes load on demand

### Module Federation Patterns
- **Dynamic Remotes**: Runtime URL configuration
- **Error Boundaries**: Graceful module failure handling
- **Preloading**: Critical modules load early
- **Health Checks**: Monitor module availability

### Security Considerations
- CORS headers configured for remote loading
- Content Security Policy for trusted origins
- No sensitive data in frontend bundles

## Migration Strategy

### Phase 1: Setup (Week 1-2)
- Create Angular workspace
- Configure Module Federation
- Setup shared library

### Phase 2: Shell Development (Week 3-4)
- Implement shell layout
- Configure routing
- Add error handling

### Phase 3: Module Migration (Week 5-8)
- Migrate one module at a time
- Validate AG Grid isolation
- Update CI/CD pipelines

### Phase 4: Production (Week 9-10)
- Performance optimization
- Monitoring setup
- Documentation
