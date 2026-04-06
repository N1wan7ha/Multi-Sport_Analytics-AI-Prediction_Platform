import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DashboardComponent } from '../../dashboard/dashboard.component';
import { AdminActivityComponent } from './admin-activity.component';
import { AdminMetricsComponent } from './admin-metrics.component';
import { AdminPipelineComponent } from './admin-pipeline.component';
import { AdminUsersComponent } from './admin-users.component';

@Component({
  selector: 'app-admin-overview',
  standalone: true,
  imports: [CommonModule, DashboardComponent, AdminActivityComponent, AdminMetricsComponent, AdminPipelineComponent, AdminUsersComponent],
  template: `
    <div class="page-container animate-fade-up" style="display:grid; gap:1rem;">
      <div class="card">
        <h2>Admin Overview</h2>
        <p class="text-secondary" style="margin-top:.45rem;">
          Unified admin dashboard with user analytics, data pipeline health, and user management plus standard user-facing dashboard insights.
        </p>
      </div>

      <app-admin-metrics></app-admin-metrics>
      <app-admin-activity></app-admin-activity>
      <app-admin-pipeline></app-admin-pipeline>
      <app-admin-users></app-admin-users>

      <div class="card">
        <h3>User Dashboard Mirror</h3>
        <p class="text-secondary" style="margin-top:.45rem;">
          Same operational surfaces available to users, visible to admins for parity checks.
        </p>
      </div>
      <app-dashboard></app-dashboard>
    </div>
  `,
})
export class AdminOverviewComponent {}
