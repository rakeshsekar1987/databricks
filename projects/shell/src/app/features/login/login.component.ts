import { Component, OnInit, ChangeDetectionStrategy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { USE_MOCK_AUTH } from '../../core/auth/auth.config';

/**
 * Login Component
 * 
 * Provides SSO login via OAuth 2.0 with domain_name.com
 * Supports both OAuth flow and mock authentication for development.
 */
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <div class="logo">📊</div>
          <h1>UI Module Federation</h1>
          <p class="subtitle">Sign in to access the platform</p>
        </div>
        
        @if (authService.authError()) {
          <div class="error-message">
            <span class="error-icon">⚠️</span>
            {{ authService.authError() }}
          </div>
        }
        
        <div class="login-body">
          <!-- SSO Login Button -->
          <button 
            class="btn-sso" 
            (click)="loginWithSSO()"
            [disabled]="isLoading()">
            @if (isLoading()) {
              <span class="spinner"></span>
              <span>Signing in...</span>
            } @else {
              <span class="sso-icon">🔐</span>
              <span>Sign in with domain_name.com</span>
            }
          </button>
          
          <div class="divider">
            <span>or</span>
          </div>
          
          <!-- Demo Login for Development -->
          @if (useMockAuth) {
            <div class="demo-section">
              <p class="demo-label">Development Mode</p>
              <button 
                class="btn-demo" 
                (click)="loginDemo()"
                [disabled]="isLoading()">
                👤 Continue as Demo User
              </button>
            </div>
          }
        </div>
        
        <div class="login-footer">
          <p class="footer-text">
            By signing in, you agree to our 
            <a href="#">Terms of Service</a> and 
            <a href="#">Privacy Policy</a>
          </p>
          
          <div class="tech-info">
            <span class="tech-badge">OAuth 2.0</span>
            <span class="tech-badge">PKCE</span>
            <span class="tech-badge">Angular 17</span>
          </div>
        </div>
      </div>
      
      <div class="login-features">
        <h2>Platform Features</h2>
        <ul class="feature-list">
          <li>
            <span class="feature-icon">🏗️</span>
            <div>
              <strong>Module Federation</strong>
              <p>Independent micro-frontends with runtime loading</p>
            </div>
          </li>
          <li>
            <span class="feature-icon">📊</span>
            <div>
              <strong>Multiple AG Grid Versions</strong>
              <p>v29, v30, v31 running simultaneously</p>
            </div>
          </li>
          <li>
            <span class="feature-icon">🎨</span>
            <div>
              <strong>Motif Design System</strong>
              <p>Consistent UI across all modules</p>
            </div>
          </li>
          <li>
            <span class="feature-icon">🚀</span>
            <div>
              <strong>Independent Deployments</strong>
              <p>Deploy modules without affecting others</p>
            </div>
          </li>
        </ul>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 48px;
      padding: 24px;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    .login-card {
      width: 420px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      overflow: hidden;
    }
    
    .login-header {
      text-align: center;
      padding: 40px 32px 24px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
    
    .logo {
      font-size: 3rem;
      margin-bottom: 16px;
    }
    
    .login-header h1 {
      margin: 0 0 8px 0;
      font-size: 1.5rem;
      font-weight: 600;
    }
    
    .subtitle {
      margin: 0;
      opacity: 0.9;
      font-size: 0.95rem;
    }
    
    .error-message {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 16px 24px 0;
      padding: 12px 16px;
      background: #ffebee;
      color: #c62828;
      border-radius: 8px;
      font-size: 0.9rem;
    }
    
    .login-body {
      padding: 32px;
    }
    
    .btn-sso {
      width: 100%;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: #1976d2;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .btn-sso:hover:not(:disabled) {
      background: #1565c0;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(25, 118, 210, 0.4);
    }
    
    .btn-sso:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }
    
    .sso-icon {
      font-size: 1.25rem;
    }
    
    .spinner {
      width: 20px;
      height: 20px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    
    .divider {
      display: flex;
      align-items: center;
      margin: 24px 0;
      color: #999;
      font-size: 0.85rem;
    }
    
    .divider::before,
    .divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background: #e0e0e0;
    }
    
    .divider span {
      padding: 0 16px;
    }
    
    .demo-section {
      text-align: center;
    }
    
    .demo-label {
      margin: 0 0 12px 0;
      font-size: 0.8rem;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .btn-demo {
      width: 100%;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: #f5f5f5;
      color: #333;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      font-size: 0.95rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .btn-demo:hover:not(:disabled) {
      background: #eeeeee;
      border-color: #bdbdbd;
    }
    
    .login-footer {
      padding: 24px 32px;
      background: #fafafa;
      border-top: 1px solid #e0e0e0;
      text-align: center;
    }
    
    .footer-text {
      margin: 0 0 16px 0;
      font-size: 0.8rem;
      color: #666;
    }
    
    .footer-text a {
      color: #1976d2;
    }
    
    .tech-info {
      display: flex;
      justify-content: center;
      gap: 8px;
    }
    
    .tech-badge {
      padding: 4px 8px;
      background: #e3f2fd;
      color: #1565c0;
      font-size: 0.7rem;
      font-weight: 600;
      border-radius: 4px;
    }
    
    .login-features {
      width: 400px;
      color: white;
    }
    
    .login-features h2 {
      margin: 0 0 24px 0;
      font-size: 1.5rem;
      font-weight: 600;
    }
    
    .feature-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    
    .feature-list li {
      display: flex;
      gap: 16px;
      padding: 16px 0;
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .feature-list li:last-child {
      border-bottom: none;
    }
    
    .feature-icon {
      font-size: 2rem;
    }
    
    .feature-list strong {
      display: block;
      margin-bottom: 4px;
      font-size: 1rem;
    }
    
    .feature-list p {
      margin: 0;
      font-size: 0.9rem;
      opacity: 0.8;
    }
    
    @media (max-width: 900px) {
      .login-container {
        flex-direction: column;
      }
      
      .login-features {
        display: none;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginComponent implements OnInit {
  readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  
  isLoading = signal(false);
  useMockAuth = USE_MOCK_AUTH;
  
  ngOnInit(): void {
    // If already authenticated, redirect to home
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/']);
    }
  }
  
  loginWithSSO(): void {
    this.isLoading.set(true);
    this.authService.login();
  }
  
  loginDemo(): void {
    this.isLoading.set(true);
    this.authService.login();
  }
}
