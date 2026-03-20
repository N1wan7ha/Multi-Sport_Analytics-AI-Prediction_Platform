import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

import { environment } from '../../../../environments/environment';

interface SystemMetrics {
  total_users: number;
  active_users: number;
  live_matches: number;
  queued_predictions: number;
  processing_predictions: number;
  failed_predictions: number;
  completed_predictions: number;
}

interface TrendCard {
  title: string;
  subtitle: string;
  valueLabel: string;
  bars: number[];
}

@Component({
  selector: 'app-admin-metrics',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <h3>System Metrics</h3>
      <p class="text-secondary" style="margin-top:.5rem;">Operational counters for admin monitoring.</p>

      <p *ngIf="error" class="status-error" style="margin-top:.8rem;">{{ error }}</p>

      <div *ngIf="metrics" style="margin-top:1rem; display:grid; gap:.75rem; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));">
        <div class="stat-card">
          <div class="stat-card__label">Total Users</div>
          <div class="stat-card__value">{{ metrics.total_users }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">Active Users</div>
          <div class="stat-card__value">{{ metrics.active_users }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">Live Matches</div>
          <div class="stat-card__value">{{ metrics.live_matches }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">Queued Jobs</div>
          <div class="stat-card__value">{{ metrics.queued_predictions }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">Processing Jobs</div>
          <div class="stat-card__value">{{ metrics.processing_predictions }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">Failed Jobs</div>
          <div class="stat-card__value">{{ metrics.failed_predictions }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">Completed Jobs</div>
          <div class="stat-card__value">{{ metrics.completed_predictions }}</div>
        </div>
      </div>

      <div *ngIf="trendCards.length" style="margin-top:1rem; display:grid; gap:.75rem; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));">
        <div class="trend-card" *ngFor="let card of trendCards">
          <div class="trend-card__head">
            <div>
              <div class="trend-card__title">{{ card.title }}</div>
              <div class="trend-card__subtitle">{{ card.subtitle }}</div>
            </div>
            <div class="trend-card__value">{{ card.valueLabel }}</div>
          </div>

          <div class="sparkline" [attr.aria-label]="card.title + ' trend'">
            <div class="sparkline__bar" *ngFor="let bar of card.bars" [style.height.%]="bar"></div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .trend-card {
        border: 1px solid var(--border-primary);
        border-radius: 12px;
        padding: .8rem;
        background: color-mix(in oklab, var(--surface-secondary) 85%, #0b1321 15%);
      }

      .trend-card__head {
        display: flex;
        justify-content: space-between;
        gap: .5rem;
        align-items: baseline;
      }

      .trend-card__title {
        font-weight: 700;
        font-size: .93rem;
      }

      .trend-card__subtitle {
        color: var(--text-secondary);
        font-size: .75rem;
      }

      .trend-card__value {
        color: var(--color-accent);
        font-weight: 700;
        font-size: .9rem;
      }

      .sparkline {
        margin-top: .65rem;
        height: 44px;
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        align-items: end;
        gap: .25rem;
      }

      .sparkline__bar {
        border-radius: 4px 4px 2px 2px;
        background: linear-gradient(180deg, var(--color-accent), color-mix(in oklab, var(--color-accent) 55%, #0f1729 45%));
      }
    `,
  ],
})
export class AdminMetricsComponent implements OnInit {
  metrics: SystemMetrics | null = null;
  trendCards: TrendCard[] = [];
  error = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http.get<SystemMetrics>(`${environment.apiUrl}/admin/system-metrics/`).subscribe({
      next: (response) => {
        this.metrics = response;
        this.trendCards = this.buildTrendCards(response);
      },
      error: () => {
        this.error = 'Failed to load system metrics';
      },
    });
  }

  private buildTrendCards(metrics: SystemMetrics): TrendCard[] {
    const totalUsers = Math.max(metrics.total_users, 1);
    const jobsTotal = Math.max(
      metrics.queued_predictions + metrics.processing_predictions + metrics.failed_predictions + metrics.completed_predictions,
      1
    );

    const activeUsersPct = Math.round((metrics.active_users / totalUsers) * 100);
    const completionPct = Math.round((metrics.completed_predictions / jobsTotal) * 100);
    const failurePct = Math.round((metrics.failed_predictions / jobsTotal) * 100);
    const inflightPct = Math.round(((metrics.queued_predictions + metrics.processing_predictions) / jobsTotal) * 100);

    return [
      {
        title: 'User Engagement',
        subtitle: 'Active users share',
        valueLabel: `${activeUsersPct}%`,
        bars: this.makeSparkline(activeUsersPct),
      },
      {
        title: 'Job Success Rate',
        subtitle: 'Completed prediction share',
        valueLabel: `${completionPct}%`,
        bars: this.makeSparkline(completionPct),
      },
      {
        title: 'Failure Pressure',
        subtitle: 'Failed prediction share',
        valueLabel: `${failurePct}%`,
        bars: this.makeSparkline(failurePct),
      },
      {
        title: 'Queue Load',
        subtitle: 'Pending + processing share',
        valueLabel: `${inflightPct}%`,
        bars: this.makeSparkline(inflightPct),
      },
    ];
  }

  private makeSparkline(value: number): number[] {
    const baseline = this.clamp(value, 6, 96);
    const offsets = [-20, -14, -10, -7, -3, 0, 2, 5, 3, 6, 4, 0];
    return offsets.map((offset) => this.clamp(baseline + offset, 6, 100));
  }

  private clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
  }
}
