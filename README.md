# Angular Module Federation Platform

A **production-ready** micro-frontend architecture using Angular 17 with Webpack 5 Module Federation, enabling independent development, deployment, and versioning of UI modules with support for **multiple AG Grid versions** and **Motif Design System** integration.

## Quick Start

### Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation

```bash
# Install dependencies
npm install --legacy-peer-deps

# Build shared library
npm run build:shared
```

### Development

**Option 1: Start all modules**
```bash
./scripts/dev.sh
```

**Option 2: Start modules individually** (in separate terminals)
```bash
# Terminal 1 - Shell (Host) on port 4200
npm run start:shell

# Terminal 2 - Tax Reporting (AG Grid v29) on port 4204
npm run start:tax-reporting

# Terminal 3 - Financial Reporting (AG Grid v30) on port 4202
npm run start:financial-reporting

# ... other modules on ports 4201, 4203, 4205
```

**Option 3: Docker Compose**
```bash
cd infrastructure/docker
docker-compose up --build
```

### Access the Application

| Module | URL | AG Grid Version |
|--------|-----|-----------------|
| **Shell (Host)** | http://localhost:4200 | - |
| Reg Reporting | http://localhost:4201 | v31.0.0 |
| Financial Reporting | http://localhost:4202 | v30.2.0 |
| Expense Reporting | http://localhost:4203 | v31.0.0 |
| Tax Reporting | http://localhost:4204 | v29.3.0 |
| Control Tower | http://localhost:4205 | v31.0.0 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Shell Application                               │
│                    (Angular 17 Host + Module Federation)                     │
│                      Dynamic Remote Loading + Routing                        │
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
         │              │              │              │              │
         └──────────────┴──────────────┼──────────────┴──────────────┘
                                       ▼
                          ┌─────────────────────────┐
                          │    Shared Library       │
                          │  - Motif Components     │
                          │  - Common Services      │
                          │  - Utility Functions    │
                          └─────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Angular 17** | Latest Angular with standalone components and signals |
| **Module Federation** | Webpack 5 for dynamic runtime module loading |
| **Motif Design System** | Shared UI component library across all modules |
| **Multiple AG Grid Versions** | Run v29, v30, v31 simultaneously |
| **Independent Deployments** | Each module deploys without affecting others |
| **Production Ready** | Docker, Kubernetes, and CI/CD pipelines included |

---

## Project Structure

```
angular-module-federation/
├── projects/
│   ├── shell/                      # Host application
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── core/           # Core services, guards, interceptors
│   │   │   │   ├── shared/         # Shared components, directives, pipes
│   │   │   │   ├── features/       # Feature modules (home, error)
│   │   │   │   ├── layouts/        # Layout components (header, sidebar, footer)
│   │   │   │   ├── app.component.ts
│   │   │   │   ├── app.config.ts
│   │   │   │   └── app.routes.ts
│   │   │   ├── environments/       # Environment configurations
│   │   │   └── styles.scss         # Global styles with Motif CSS variables
│   │   ├── webpack.config.js       # Module Federation config
│   │   └── tsconfig.app.json
│   │
│   ├── reg-reporting/              # Remote module - AG Grid v31
│   ├── financial-reporting/        # Remote module - AG Grid v30
│   ├── expense-reporting/          # Remote module - AG Grid v31
│   ├── tax-reporting/              # Remote module - AG Grid v29
│   ├── control-tower/              # Remote module - AG Grid v31
│   │
│   └── shared-lib/                 # Shared library with Motif integration
│       ├── src/
│       │   ├── lib/
│       │   │   ├── components/     # Button, Card, Alert, Badge, Modal, Spinner
│       │   │   ├── services/       # Notification, Storage, API services
│       │   │   ├── models/         # Common TypeScript interfaces
│       │   │   └── utils/          # Formatters, Validators
│       │   └── public-api.ts       # Public exports
│       └── ng-package.json
│
├── infrastructure/
│   ├── docker/                     # Docker configurations
│   │   ├── Dockerfile.shell
│   │   ├── Dockerfile.module
│   │   ├── docker-compose.yml
│   │   └── nginx/
│   └── kubernetes/                 # Kubernetes manifests
│
├── scripts/
│   ├── dev.sh                      # Development startup
│   ├── build.sh                    # Production build
│   └── docker-build.sh             # Docker image build
│
├── .github/workflows/              # CI/CD pipelines
│   ├── shell.yml
│   └── modules.yml
│
├── angular.json                    # Angular workspace configuration
├── package.json                    # Root dependencies
└── tsconfig.json                   # TypeScript configuration
```

---

## How Module Federation Works

### Shell (Host) Configuration

```javascript
// projects/shell/webpack.config.js
new ModuleFederationPlugin({
  name: 'shell',
  remotes: {
    taxReporting: 'taxReporting@http://localhost:4204/remoteEntry.js',
    regReporting: 'regReporting@http://localhost:4201/remoteEntry.js',
  },
  shared: {
    '@angular/core': { singleton: true },
    '@angular/common': { singleton: true },
    '@mfs/motif': { singleton: true },  // Shared Motif library
    // AG Grid is NOT shared - each module has its own version
  },
})
```

### Remote Module Configuration (Tax Reporting with AG Grid v29)

```javascript
// projects/tax-reporting/webpack.config.js
new ModuleFederationPlugin({
  name: 'taxReporting',
  filename: 'remoteEntry.js',
  exposes: {
    './routes': './projects/tax-reporting/src/app/app.routes.ts',
  },
  shared: {
    '@angular/core': { singleton: true },
    '@mfs/motif': { singleton: true },
    'ag-grid-community': {
      singleton: false,           // NOT singleton - allows v29
      requiredVersion: '^29.3.0',
    },
  },
})
```

### Dynamic Route Loading

```typescript
// projects/shell/src/app/app.routes.ts
{
  path: 'tax-reporting',
  loadChildren: () => loadRemoteModule({
    type: 'module',
    remoteEntry: 'http://localhost:4204/remoteEntry.js',
    exposedModule: './routes'
  }).then(m => m.TAX_REPORTING_ROUTES)
}
```

---

## AG Grid Version Isolation

Each module bundles its own AG Grid version because:

1. **AG Grid is NOT shared as singleton** in Module Federation config
2. **Each module declares its version** in `package.json`
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

## Shared Library (Motif Integration)

The shared library provides Motif-styled components:

```typescript
// Usage in any module
import { ButtonComponent, CardComponent, AlertComponent } from '@shared-lib';
import { NotificationService, ApiService } from '@shared-lib';
import { formatCurrency, isValidEmail } from '@shared-lib';
```

### Available Components
- `lib-button` - Primary, secondary, danger, success variants
- `lib-card` - Container with header, body, footer
- `lib-alert` - Info, success, warning, error alerts
- `lib-badge` - Status badges
- `lib-spinner` - Loading indicator
- `lib-modal` - Dialog overlay

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
kubectl apply -k infrastructure/kubernetes/
```

---

## CI/CD Pipelines

Each module has independent CI/CD with path-based triggers:

```yaml
# .github/workflows/modules.yml
on:
  push:
    paths:
      - 'projects/tax-reporting/**'  # Only triggers for this module
      - 'projects/shared-lib/**'
```

### Pipeline Stages

1. **Build** - Compile Angular, bundle with Webpack
2. **Test** - Run unit tests and linting
3. **Docker** - Build and push container images
4. **Deploy** - Deploy to Kubernetes

---

## Best Practices Implemented

### Angular Best Practices
- Standalone components (no NgModules)
- Signals for reactive state
- OnPush change detection
- Lazy loading for all routes
- Strict TypeScript configuration

### Module Federation Best Practices
- Singleton sharing for framework libraries
- Version isolation for AG Grid
- Dynamic remote loading with error handling
- Graceful degradation when modules fail

### Project Structure Best Practices
- Feature-based organization
- Core module for services/guards
- Shared module for common components
- Environment-specific configurations
- Comprehensive typing with TypeScript

---

## Test Cases

### 1.1 OAuth 2.0 SSO Login with domain_name.com

The POC implements OAuth 2.0 Authentication with PKCE flow:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Browser   │────▶│  Shell App       │────▶│ domain_name.com │
│             │     │  /login          │     │ OAuth Provider  │
└─────────────┘     └──────────────────┘     └─────────────────┘
                           │                         │
                           │ 1. Generate PKCE        │
                           │ 2. Redirect to          │
                           │    /oauth2/authorize    │
                           │                         │
                           │◀────────────────────────│
                           │ 3. Auth Code Callback   │
                           │                         │
                           │ 4. Exchange Code        │────▶
                           │    for Tokens           │
                           │                         │◀────
                           │ 5. Store Token          │
                           │ 6. Navigate to Home     │
```

**Files:**
- `projects/shell/src/app/core/auth/auth.service.ts` - OAuth logic
- `projects/shell/src/app/core/auth/auth.guard.ts` - Route protection
- `projects/shell/src/app/features/login/login.component.ts` - Login UI

**Testing:**
1. Navigate to `http://localhost:4200/login`
2. Click "Continue as Demo User" (mock mode enabled by default)
3. User is authenticated and redirected to home

### 1.2 Module-to-Module Navigation

All remote modules include cross-navigation capabilities:

| From Module | Navigation Options |
|-------------|-------------------|
| Reg Reporting | Financial, Expense, Tax, Control Tower |
| Financial Reporting | Reg, Expense, Tax, Control Tower |
| Expense Reporting | Reg, Financial, Tax, Control Tower |
| Tax Reporting | Reg, Financial, Expense, Control Tower |
| Control Tower | All modules with full descriptions |

**Testing:**
1. Login and navigate to any module (e.g., `/tax-reporting`)
2. Scroll to "Navigate to Other Modules" section
3. Click any module card to navigate
4. Verify seamless transition between modules

### 1.3 Mock JSON Data

Mock data files are provided for all modules:

| File | Content | Location |
|------|---------|----------|
| `tax-reports.json` | 8 tax filings with status, liability | `/assets/mock-data/` |
| `financial-statements.json` | 6 income statements, balance sheets | `/assets/mock-data/` |
| `regulatory-reports.json` | 7 compliance reports (Basel III, MiFID) | `/assets/mock-data/` |
| `expenses.json` | 8 expense records with categories | `/assets/mock-data/` |
| `modules-status.json` | Health metrics for Control Tower | `/assets/mock-data/` |

**Usage:**
```typescript
import { MockDataService } from './core/services/mock-data.service';

constructor(private mockDataService: MockDataService) {}

ngOnInit() {
  this.mockDataService.getTaxReports().subscribe(data => {
    this.rowData = data;
  });
}
```

---

## Troubleshooting

### Module fails to load

1. Check if the remote module is running
2. Verify CORS headers are configured
3. Check browser console for specific errors
4. Verify `remoteEntry.js` is accessible

### AG Grid version conflicts

1. Ensure `singleton: false` in webpack shared config
2. Check that each module has correct version in `package.json`
3. Clear browser cache and rebuild

### Build errors

```bash
# Clean and rebuild
rm -rf node_modules dist
npm install --legacy-peer-deps
npm run build:shared
npm run build
```

---

## License

MIT
