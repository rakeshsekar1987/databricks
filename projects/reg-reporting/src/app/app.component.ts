import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  template: `
    <div class="reg-reporting-standalone">
      <header class="standalone-header">
        <h1>Regulatory Reporting Module</h1>
        <span class="version-badge">AG Grid v31</span>
      </header>
      <main><router-outlet></router-outlet></main>
    </div>
  `,
  styles: [`
    .reg-reporting-standalone { min-height: 100vh; background: #f5f5f5; }
    .standalone-header { display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: #1a1a2e; color: white; }
    .standalone-header h1 { margin: 0; font-size: 1.5rem; }
    .version-badge { padding: 4px 8px; background: rgba(255,255,255,0.2); border-radius: 4px; font-size: 0.8rem; }
    main { padding: 24px; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AppComponent {}
