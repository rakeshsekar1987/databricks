import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

/**
 * Tax Details Component
 * 
 * Displays detailed information for a specific tax report.
 */
@Component({
  selector: 'app-tax-details',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="details-container">
      <div class="breadcrumb">
        <a routerLink="/tax-reporting">Tax Reporting</a>
        <span>/</span>
        <span>Details</span>
      </div>
      
      <div class="details-card">
        <h2>Tax Report Details</h2>
        <p>Report ID: {{ reportId }}</p>
        <p>Additional details would be loaded here...</p>
        
        <a routerLink="/tax-reporting" class="back-link">
          ← Back to Tax Reports
        </a>
      </div>
    </div>
  `,
  styles: [`
    .details-container {
      padding: 24px;
    }
    
    .breadcrumb {
      display: flex;
      gap: 8px;
      margin-bottom: 24px;
      color: #6b7280;
    }
    
    .breadcrumb a {
      color: #7c3aed;
    }
    
    .details-card {
      background: white;
      padding: 24px;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .back-link {
      display: inline-block;
      margin-top: 24px;
      color: #7c3aed;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TaxDetailsComponent {
  reportId: string;
  
  constructor(private route: ActivatedRoute) {
    this.reportId = this.route.snapshot.params['id'] || 'Unknown';
  }
}
