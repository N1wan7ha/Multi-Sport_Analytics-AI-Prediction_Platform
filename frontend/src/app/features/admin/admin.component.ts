import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterOutlet],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card" style="margin-bottom:1rem;">
        <h1>Admin Panel</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Manage users, pipelines, and system metrics.</p>

        <div style="display:flex; gap:.5rem; margin-top:1rem; flex-wrap:wrap;">
          <a routerLink="users" class="btn btn-primary">👥 Users</a>
          <a routerLink="activity" class="btn btn-secondary">📊 Activity</a>
          <a routerLink="pipeline" class="btn btn-secondary">⚙ Pipeline</a>
          <a routerLink="metrics" class="btn btn-secondary">📈 Metrics</a>
          <a routerLink="predictions" class="btn btn-secondary">🧠 Predictions</a>
        </div>
      </div>

      <router-outlet></router-outlet>
    </div>
  `,
})
export class AdminDashboardComponent {}
