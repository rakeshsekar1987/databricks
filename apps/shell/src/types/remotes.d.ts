// Type declarations for remote federated modules
// These allow TypeScript to understand the remote module imports

declare module 'regReporting/App' {
  const App: React.ComponentType;
  export default App;
}

declare module 'financialReporting/App' {
  const App: React.ComponentType;
  export default App;
}

declare module 'expenseReporting/App' {
  const App: React.ComponentType;
  export default App;
}

declare module 'taxReporting/App' {
  const App: React.ComponentType;
  export default App;
}

declare module 'controlTower/App' {
  const App: React.ComponentType;
  export default App;
}

// Extend for more exports from each module as needed
declare module 'regReporting/*' {
  const component: React.ComponentType;
  export default component;
}

declare module 'financialReporting/*' {
  const component: React.ComponentType;
  export default component;
}

declare module 'expenseReporting/*' {
  const component: React.ComponentType;
  export default component;
}

declare module 'taxReporting/*' {
  const component: React.ComponentType;
  export default component;
}

declare module 'controlTower/*' {
  const component: React.ComponentType;
  export default component;
}
