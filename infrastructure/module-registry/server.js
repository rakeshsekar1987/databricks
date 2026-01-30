/**
 * Module Registry Service
 * Provides dynamic module discovery for the Module Federation architecture
 */

const http = require('http');
const url = require('url');

const PORT = process.env.PORT || 4000;

// In-memory module registry
// In production, this would be stored in a database
const moduleRegistry = {
  regReporting: {
    name: 'Regulatory Reporting',
    scope: 'regReporting',
    module: './App',
    remoteEntry: process.env.REG_REPORTING_URL || 'http://localhost:3001/remoteEntry.js',
    version: '2.1.0',
    agGridVersion: '31.0.0',
    status: 'active',
    updatedAt: new Date().toISOString(),
  },
  financialReporting: {
    name: 'Financial Reporting',
    scope: 'financialReporting',
    module: './App',
    remoteEntry: process.env.FINANCIAL_REPORTING_URL || 'http://localhost:3002/remoteEntry.js',
    version: '1.5.2',
    agGridVersion: '30.2.0',
    status: 'active',
    updatedAt: new Date().toISOString(),
  },
  expenseReporting: {
    name: 'Expense Reporting',
    scope: 'expenseReporting',
    module: './App',
    remoteEntry: process.env.EXPENSE_REPORTING_URL || 'http://localhost:3003/remoteEntry.js',
    version: '1.2.0',
    agGridVersion: '31.0.0',
    status: 'active',
    updatedAt: new Date().toISOString(),
  },
  taxReporting: {
    name: 'Tax Reporting',
    scope: 'taxReporting',
    module: './App',
    remoteEntry: process.env.TAX_REPORTING_URL || 'http://localhost:3004/remoteEntry.js',
    version: '3.0.1',
    agGridVersion: '29.3.0',
    status: 'active',
    updatedAt: new Date().toISOString(),
  },
  controlTower: {
    name: 'Control Tower',
    scope: 'controlTower',
    module: './App',
    remoteEntry: process.env.CONTROL_TOWER_URL || 'http://localhost:3005/remoteEntry.js',
    version: '1.0.0',
    agGridVersion: '31.0.0',
    status: 'active',
    updatedAt: new Date().toISOString(),
  },
};

// Request handler
const requestHandler = (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const path = parsedUrl.pathname;
  const method = req.method;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Health check
  if (path === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'healthy', timestamp: new Date().toISOString() }));
    return;
  }

  // Get all modules manifest
  if (path === '/api/module-manifest' && method === 'GET') {
    const manifest = {
      name: 'UI Platform',
      version: '1.0.0',
      modules: moduleRegistry,
      updatedAt: new Date().toISOString(),
    };
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(manifest));
    return;
  }

  // Get single module
  const moduleMatch = path.match(/^\/api\/modules\/([a-zA-Z-]+)$/);
  if (moduleMatch && method === 'GET') {
    const moduleName = moduleMatch[1];
    const module = moduleRegistry[moduleName];
    
    if (module) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(module));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Module not found' }));
    }
    return;
  }

  // Update module (POST)
  if (moduleMatch && method === 'POST') {
    const moduleName = moduleMatch[1];
    let body = '';
    
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const updates = JSON.parse(body);
        
        if (moduleRegistry[moduleName]) {
          moduleRegistry[moduleName] = {
            ...moduleRegistry[moduleName],
            ...updates,
            updatedAt: new Date().toISOString(),
          };
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(moduleRegistry[moduleName]));
        } else {
          moduleRegistry[moduleName] = {
            ...updates,
            status: 'active',
            updatedAt: new Date().toISOString(),
          };
          res.writeHead(201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(moduleRegistry[moduleName]));
        }
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON' }));
      }
    });
    return;
  }

  // Get AG Grid versions summary
  if (path === '/api/ag-grid-versions' && method === 'GET') {
    const versions = Object.entries(moduleRegistry).map(([key, module]) => ({
      module: key,
      name: module.name,
      agGridVersion: module.agGridVersion,
    }));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ versions }));
    return;
  }

  // 404 for unhandled routes
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
};

const server = http.createServer(requestHandler);

server.listen(PORT, () => {
  console.log(`Module Registry running on port ${PORT}`);
  console.log('Registered modules:');
  Object.entries(moduleRegistry).forEach(([key, module]) => {
    console.log(`  - ${key}: AG Grid v${module.agGridVersion}`);
  });
});
