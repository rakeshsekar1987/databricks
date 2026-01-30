/**
 * Application Entry Point
 * Uses dynamic import for Module Federation compatibility
 */

// Import bootstrap asynchronously to allow Module Federation to initialize
import('./bootstrap').catch((error) => {
  console.error('Failed to load application:', error);
  
  // Display error message to user
  const root = document.getElementById('root');
  if (root) {
    root.innerHTML = `
      <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100vh;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        text-align: center;
        padding: 20px;
      ">
        <h1 style="color: #e53e3e; margin-bottom: 16px;">Application Failed to Load</h1>
        <p style="color: #4a5568; margin-bottom: 24px;">
          ${error.message || 'An unexpected error occurred'}
        </p>
        <button 
          onclick="window.location.reload()" 
          style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
          "
        >
          Reload Page
        </button>
      </div>
    `;
  }
});
