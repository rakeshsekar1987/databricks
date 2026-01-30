# UI Platform - Module Federation POC

A **production-ready** micro-frontend architecture using Webpack 5 Module Federation, enabling independent development, deployment, and versioning of UI modules with support for **multiple AG Grid versions**.

## Quick Start

### Prerequisites

- Node.js >= 18.0.0
- pnpm >= 8.0.0 (`npm install -g pnpm`)

### Installation

```bash
# Clone and install dependencies
pnpm install

# Build shared library
pnpm build:shared
```

### Development

**Option 1: Start all modules**
```bash
./scripts/dev.sh
```

**Option 2: Start modules individually** (in separate terminals)
```bash
# Terminal 1 - Shell (Host) on port 3000
pnpm --filter @platform/shell dev

# Terminal 2 - Tax Reporting (AG Grid v29) on port 3004
pnpm --filter @platform/tax-reporting dev

# Terminal 3 - Financial Reporting (AG Grid v30) on port 3002
pnpm --filter @platform/financial-reporting dev

# ... other modules on ports 3001, 3003, 3005
```

**Option 3: Docker Compose**
```bash
cd infrastructure/docker
docker-compose up --build
```

### Access the Application

| Module | URL | AG Grid Version |
|--------|-----|-----------------|
| **Shell (Host)** | http://localhost:3000 | - |
| Reg Reporting | http://localhost:3001 | v31.0.0 |
| Financial Reporting | http://localhost:3002 | v30.2.0 |
| Expense Reporting | http://localhost:3003 | v31.0.0 |
| Tax Reporting | http://localhost:3004 | v29.3.0 |
| Control Tower | http://localhost:3005 | v31.0.0 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Shell Application                               │
│                         (Main UI Container/Host)                            │
│                      Module Federation Runtime                              │
└─────────────────────────────────────────────────────────────────────────────┘
         │              │              │              │              │
         ▼              ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│     Reg     │ │  Financial  │ │   Expense   │ │     Tax     │ │   Control   │
│  Reporting  │ │  Reporting  │ │  Reporting  │ │  Reporting  │ │    Tower    │
│             │ │             │ │             │ │             │ │             │
│ AG Grid v31 │ │ AG Grid v30 │ │ AG Grid v31 │ │ AG Grid v29 │ │ AG Grid v31 │
│ ─────────── │ │ ─────────── │ │ ─────────── │ │ ─────────── │ │ ─────────── │
│ Independent │ │ Independent │ │ Independent │ │ Independent │ │ Independent │
│    Pod      │ │    Pod      │ │    Pod      │ │    Pod      │ │    Pod      │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Independent Deployments** | Each module deploys independently without affecting others |
| **Multiple AG Grid Versions** | Run v29, v30, v31 simultaneously in the same application |
| **Dynamic Module Loading** | Load remote modules at runtime with error handling |
| **Team Autonomy** | Teams own modules end-to-end with full deployment independence |
| **Fast Builds** | Only rebuild changed modules (80% faster) |
| **Graceful Degradation** | Modules fail independently with retry capability |

---

## Project Structure

```
ui-module-federation/
├── apps/
│   ├── shell/                    # Host application
│   │   ├── src/
│   │   │   ├── lib/              # Module Federation utilities
│   │   │   ├── components/       # React components
│   │   │   ├── pages/            # Page components
│   │   │   └── styles/           # CSS styles
│   │   ├── webpack.config.js     # Production-ready webpack
│   │   └── package.json
│   │
│   ├── tax-reporting/            # AG Grid v29
│   ├── financial-reporting/      # AG Grid v30
│   ├── reg-reporting/            # AG Grid v31
│   ├── expense-reporting/        # AG Grid v31
│   └── control-tower/            # AG Grid v31
│
├── packages/
│   └── shared-library/           # Shared components & utilities
│
├── infrastructure/
│   ├── docker/                   # Production Docker configs
│   │   ├── Dockerfile.shell
│   │   ├── Dockerfile.module
│   │   ├── docker-compose.yml
│   │   └── nginx/
│   ├── kubernetes/               # K8s manifests
│   └── module-registry/          # Dynamic module discovery
│
├── scripts/
│   ├── dev.sh                    # Development startup
│   ├── build.sh                  # Production build
│   └── docker-build.sh           # Docker image build
│
└── .github/workflows/            # CI/CD pipelines
```

---

## How Module Federation Works

### Shell (Host) Configuration

```javascript
// apps/shell/webpack.config.js
new ModuleFederationPlugin({
  name: 'shell',
  remotes: {
    taxReporting: 'taxReporting@http://localhost:3004/remoteEntry.js',
    regReporting: 'regReporting@http://localhost:3001/remoteEntry.js',
  },
  shared: {
    react: { singleton: true },    // Shared as singleton
    'react-dom': { singleton: true },
    // AG Grid is NOT shared - each module has its own version
  },
})
```

### Remote Module Configuration (Tax Reporting with AG Grid v29)

```javascript
// apps/tax-reporting/webpack.config.js
new ModuleFederationPlugin({
  name: 'taxReporting',
  filename: 'remoteEntry.js',
  exposes: {
    './App': './src/App',
  },
  shared: {
    react: { singleton: true },
    'ag-grid-community': {
      singleton: false,           // NOT singleton - allows v29
      requiredVersion: '^29.3.0',
    },
  },
})
```

### Dynamic Remote Loading

```typescript
// apps/shell/src/lib/moduleFederation.ts
export async function loadRemoteModule(config) {
  // Load remote entry script
  await loadScript(config.url);
  
  // Get container from window
  const container = window[config.scope];
  
  // Initialize with shared scope
  await container.init(__webpack_share_scopes__.default);
  
  // Get and return the module
  const factory = await container.get(config.module);
  return factory().default;
}
```

---

## AG Grid Version Isolation

Each module can use a different AG Grid version because:

1. **AG Grid is not shared as singleton** in Module Federation config
2. **Each module bundles its own AG Grid** version
3. **Modules are loaded in isolation** at runtime

```javascript
// Tax Reporting uses v29
"ag-grid-community": "^29.3.0"

// Financial Reporting uses v30
"ag-grid-community": "^30.2.0"

// Reg Reporting uses v31
"ag-grid-community": "^31.0.0"
```

---

## Production Deployment

### Build for Production

```bash
# Build all modules
./scripts/build.sh

# Build specific module
./scripts/build.sh tax-reporting
```

### Docker Deployment

```bash
# Build all Docker images
./scripts/docker-build.sh

# Run with Docker Compose
cd infrastructure/docker
docker-compose up -d
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -k infrastructure/kubernetes/
```

---

## CI/CD Pipelines

Each module has its own GitHub Actions workflow with path-based triggers:

```yaml
# .github/workflows/tax-reporting.yml
on:
  push:
    paths:
      - 'apps/tax-reporting/**'    # Only triggers for this module
      - 'packages/shared-library/**'
```

### Pipeline Stages

1. **Build** - Compile TypeScript, bundle with Webpack
2. **Test** - Run unit tests and linting
3. **Publish** - Upload to JFrog Artifactory
4. **Deploy** - Deploy to CDN/Kubernetes

---

## API Reference

### Module Registry

```bash
# Get all modules
GET http://localhost:4000/api/module-manifest

# Get specific module
GET http://localhost:4000/api/modules/taxReporting

# Get AG Grid versions
GET http://localhost:4000/api/ag-grid-versions
```

### Health Checks

```bash
# Shell health
GET http://localhost:3000/health

# Module health
GET http://localhost:3004/health

# Module readiness (checks remoteEntry.js)
GET http://localhost:3004/ready
```

---

## Configuration

### Environment Variables

```bash
# .env.local
NODE_ENV=development

# Remote module URLs
REG_REPORTING_URL=http://localhost:3001/remoteEntry.js
FINANCIAL_REPORTING_URL=http://localhost:3002/remoteEntry.js
EXPENSE_REPORTING_URL=http://localhost:3003/remoteEntry.js
TAX_REPORTING_URL=http://localhost:3004/remoteEntry.js
CONTROL_TOWER_URL=http://localhost:3005/remoteEntry.js

# Module Registry
MODULE_REGISTRY_URL=http://localhost:4000
```

---

## Troubleshooting

### Module fails to load

1. Check if the remote module is running
2. Verify CORS headers are configured
3. Check browser console for specific errors
4. Verify `remoteEntry.js` is accessible

### AG Grid version conflicts

1. Ensure `singleton: false` in shared config
2. Check that each module has correct version in `package.json`
3. Clear module cache and rebuild

### Build errors

```bash
# Clean all caches
pnpm clean

# Reinstall dependencies
rm -rf node_modules
pnpm install

# Rebuild
pnpm build
```

---

## Resources

- [Module Federation Documentation](https://webpack.js.org/concepts/module-federation/)
- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Presentation](./docs/presentation/module-federation-strategy.html)

---

## License

MIT
