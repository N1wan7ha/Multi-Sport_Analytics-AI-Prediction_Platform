import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Analytics</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Analytics page — coming in Phase 4.
        </p>
      </div>
    </div>
  `,
})
export class AnalyticsDashboardComponent {}
