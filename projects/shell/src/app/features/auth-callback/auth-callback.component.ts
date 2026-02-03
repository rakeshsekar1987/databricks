import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { OAuthCallbackParams } from '../../core/auth/auth.models';

/**
 * OAuth Callback Component
 * 
 * Handles the OAuth 2.0 authorization code callback.
 * Exchanges the code for tokens and redirects to the original URL.
 */
@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="callback-container">
      <div class="callback-card">
        @if (!error) {
          <div class="spinner"></div>
          <h2>Completing Sign In...</h2>
          <p>Please wait while we authenticate you.</p>
        } @else {
          <div class="error-icon">⚠️</div>
          <h2>Authentication Failed</h2>
          <p>{{ error }}</p>
          <button class="btn-retry" (click)="retryLogin()">
            Try Again
          </button>
        }
      </div>
    </div>
  `,
  styles: [`
    .callback-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    .callback-card {
      text-align: center;
      padding: 48px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }
    
    .spinner {
      width: 48px;
      height: 48px;
      margin: 0 auto 24px;
      border: 4px solid #e0e0e0;
      border-top-color: #1976d2;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    
    h2 {
      margin: 0 0 8px 0;
      color: #1a1a2e;
    }
    
    p {
      margin: 0;
      color: #666;
    }
    
    .error-icon {
      font-size: 3rem;
      margin-bottom: 16px;
    }
    
    .btn-retry {
      margin-top: 24px;
      padding: 12px 32px;
      background: #1976d2;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      cursor: pointer;
    }
    
    .btn-retry:hover {
      background: #1565c0;
    }
  `]
})
export class AuthCallbackComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  
  error: string | null = null;
  
  ngOnInit(): void {
    const queryParams = this.route.snapshot.queryParams;
    
    const callbackParams: OAuthCallbackParams = {
      code: queryParams['code'],
      state: queryParams['state'],
      error: queryParams['error'],
      errorDescription: queryParams['error_description']
    };
    
    if (callbackParams.error) {
      this.error = callbackParams.errorDescription || callbackParams.error;
      return;
    }
    
    this.authService.handleCallback(callbackParams).subscribe({
      next: (success) => {
        if (success) {
          // Redirect to original URL or home
          const redirectUrl = sessionStorage.getItem('auth_redirect_url') || '/';
          sessionStorage.removeItem('auth_redirect_url');
          this.router.navigate([redirectUrl]);
        } else {
          this.error = 'Authentication failed. Please try again.';
        }
      },
      error: () => {
        this.error = 'An error occurred during authentication.';
      }
    });
  }
  
  retryLogin(): void {
    this.router.navigate(['/login']);
  }
}
