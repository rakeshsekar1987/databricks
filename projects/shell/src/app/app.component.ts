import { Component, OnInit, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';
import { toSignal } from '@angular/core/rxjs-interop';

import { HeaderComponent } from './layouts/header/header.component';
import { SidebarComponent } from './layouts/sidebar/sidebar.component';
import { FooterComponent } from './layouts/footer/footer.component';
import { LoadingService } from './core/services/loading.service';
import { AuthService } from './core/auth/auth.service';

/**
 * Root Application Component
 * 
 * Provides the main layout structure with:
 * - Header with navigation (only when authenticated)
 * - Sidebar for module navigation (only when authenticated)
 * - Main content area with router outlet
 * - Footer with version info (only when authenticated)
 * 
 * Login and auth callback pages render without the shell layout.
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    HeaderComponent,
    SidebarComponent,
    FooterComponent
  ],
  template: `
    @if (showShellLayout()) {
      <!-- Authenticated Layout with Shell -->
      <div class="app-container">
        <app-header></app-header>
        
        <div class="app-body">
          <app-sidebar></app-sidebar>
          
          <main class="main-content" role="main">
            @if (isLoading$ | async) {
              <div class="loading-overlay">
                <div class="loading-spinner"></div>
                <p>Loading module...</p>
              </div>
            }
            
            <router-outlet></router-outlet>
          </main>
        </div>
        
        <app-footer></app-footer>
      </div>
    } @else {
      <!-- Standalone Layout for Login/Auth pages -->
      <router-outlet></router-outlet>
    }
  `,
  styles: [`
    .app-container {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      background-color: var(--motif-bg-primary, #f5f5f5);
    }
    
    .app-body {
      display: flex;
      flex: 1;
      overflow: hidden;
    }
    
    .main-content {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
      position: relative;
    }
    
    .loading-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.9);
      z-index: 100;
    }
    
    .loading-spinner {
      width: 48px;
      height: 48px;
      border: 4px solid var(--motif-border-color, #e0e0e0);
      border-top-color: var(--motif-primary, #0066cc);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AppComponent implements OnInit {
  private readonly loadingService = inject(LoadingService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  
  title = 'UI Module Federation Platform';
  isLoading$ = this.loadingService.isLoading$;
  
  // Routes that should NOT show the shell layout (header/sidebar/footer)
  private readonly standaloneRoutes = ['/login', '/auth/callback'];
  
  // Track current route to determine layout
  private readonly currentUrl = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      map(event => event.urlAfterRedirects)
    ),
    { initialValue: this.router.url }
  );
  
  /**
   * Determines if shell layout should be shown
   * Shell layout is hidden for login and auth callback pages
   */
  showShellLayout = () => {
    const url = this.currentUrl();
    const isStandaloneRoute = this.standaloneRoutes.some(route => url.startsWith(route));
    return !isStandaloneRoute && this.authService.isAuthenticated();
  };
  
  ngOnInit(): void {
    console.log('[Shell] Application initialized');
  }
}
