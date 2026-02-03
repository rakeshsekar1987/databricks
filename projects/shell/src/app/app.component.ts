import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

import { HeaderComponent } from './layouts/header/header.component';
import { SidebarComponent } from './layouts/sidebar/sidebar.component';
import { FooterComponent } from './layouts/footer/footer.component';
import { LoadingService } from './core/services/loading.service';

/**
 * Root Application Component
 * 
 * Provides the main layout structure with:
 * - Header with navigation
 * - Sidebar for module navigation
 * - Main content area with router outlet
 * - Footer with version info
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
  title = 'UI Module Federation Platform';
  isLoading$ = this.loadingService.isLoading$;
  
  constructor(private loadingService: LoadingService) {}
  
  ngOnInit(): void {
    console.log('[Shell] Application initialized');
  }
}
