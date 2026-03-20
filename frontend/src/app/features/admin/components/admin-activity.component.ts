import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ActivitySummary } from '../../../core/models';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-admin-activity',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <h3>Activity Summary</h3>
      <p class="text-secondary" style="margin-top:.5rem;">Platform activity metrics.</p>

      <div *ngIf="loading" class="text-secondary">Loading activity data...</div>
      <div *ngIf="error" style="color:#d83a52;">{{ error }}</div>

      <div *ngIf="!loading && summary" style="margin-top:1rem; display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:1rem;">
        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">New Users (7d)</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.new_registrations_7d }}</div>
        </div>

        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">New Users (30d)</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.new_registrations_30d }}</div>
        </div>

        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">Total Predictions</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.prediction_requests_total }}</div>
        </div>

        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">Pre-Match Predictions</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.pre_match }}</div>
        </div>

        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">Live Predictions</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.live }}</div>
        </div>

        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">Active Users (7d)</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.active_users_7d }}</div>
        </div>

        <div class="stat-card" style="border:1px solid #ddd; padding:1rem; border-radius:4px;">
          <div class="text-secondary" style="font-size:0.85rem;">Data Syncs (24h)</div>
          <div style="font-size:1.5rem; font-weight:bold; margin-top:.5rem;">{{ summary.syncs_24h }}</div>
        </div>
      </div>
    </div>
  `,
})
export class AdminActivityComponent implements OnInit {
  summary: ActivitySummary | null = null;
  loading = false;
  error = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadActivity();
  }

  private loadActivity(): void {
    this.loading = true;
    this.error = '';
    const apiUrl = `${environment.apiUrl}/admin/activity-summary/`;

    this.http.get<ActivitySummary>(apiUrl).subscribe({
      next: (data) => {
        this.summary = data;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load activity summary';
      },
    });
  }
}

