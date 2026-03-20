import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, Match, PipelineStatus } from '../../core/services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card hero-card" style="margin-bottom: 1rem;">
        <p class="hero-kicker">Phase 2 Dashboard</p>
        <h1>Operations Overview</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Live match pulse, pipeline readiness, and prediction activity at a glance.
        </p>

        <div class="quick-stats">
          <div class="quick-stat">
            <span>Live Matches</span>
            <strong>{{ liveMatches.length }}</strong>
          </div>
          <div class="quick-stat">
            <span>Current Feed Rows</span>
            <strong>{{ pipelineStatus?.count_cricbuzz_live ?? 0 }}</strong>
          </div>
          <div class="quick-stat">
            <span>Current Matches</span>
            <strong>{{ pipelineStatus?.count_current_matches ?? 0 }}</strong>
          </div>
        </div>
      </div>

      <div class="grid" style="display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(260px,1fr));">
        <div class="card">
          <h3>Pipeline Health</h3>
          <p *ngIf="loading" class="text-secondary">Loading status...</p>
          <p *ngIf="!loading && pipelineError" class="status-error">{{ pipelineError }}</p>
          <div *ngIf="!loading && pipelineStatus">
            <p><strong>Current matches:</strong> {{ pipelineStatus.count_current_matches }}</p>
            <p><strong>Live feed rows:</strong> {{ pipelineStatus.count_cricbuzz_live }}</p>
            <p><strong>Unified matches:</strong> {{ pipelineStatus.count_unified_matches }}</p>
            <p class="text-secondary">
              Last retraining: {{ pipelineStatus.last_model_retraining || 'N/A' }}
            </p>
          </div>
        </div>

        <div class="card">
          <h3>Live Matches</h3>
          <p *ngIf="liveError" class="status-error">{{ liveError }}</p>
          <p *ngIf="liveMatches.length === 0" class="text-secondary">No live matches right now.</p>
          <div *ngFor="let match of liveMatches.slice(0, 5)" class="list-row">
            <div><strong>{{ match.team1.name }}</strong> vs <strong>{{ match.team2.name }}</strong></div>
            <div class="text-secondary">{{ match.format | uppercase }} · {{ match.category }}</div>
          </div>
        </div>

        <div class="card">
          <h3>Live Format Mix</h3>
          <p class="text-secondary" *ngIf="formatDistribution.length === 0">No live format data yet.</p>

          <div class="bar-chart" *ngIf="formatDistribution.length > 0">
            <div class="bar-row" *ngFor="let item of formatDistribution">
              <span class="bar-label">{{ item.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" [style.width.%]="barWidth(item.value, maxFormatValue)"></div>
              </div>
              <span class="bar-value">{{ item.value }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <h3>Status Snapshot</h3>
          <div class="status-grid">
            <div class="status-item">
              <span>Pipeline Sync</span>
              <strong>{{ pipelineStatus?.last_sync_current_matches ? 'Active' : 'Unknown' }}</strong>
            </div>
            <div class="status-item">
              <span>Live Data</span>
              <strong>{{ (pipelineStatus?.count_cricbuzz_live ?? 0) > 0 ? 'Streaming' : 'Idle' }}</strong>
            </div>
            <div class="status-item">
              <span>Retraining</span>
              <strong>{{ pipelineStatus?.model_retraining_status || 'N/A' }}</strong>
            </div>
          </div>
        </div>
      </div>

      <div style="margin-top:1rem; display:flex; gap:.75rem; flex-wrap:wrap;">
        <a routerLink="/matches" class="btn btn-primary">Browse Matches</a>
        <a routerLink="/players" class="btn btn-secondary">Browse Players</a>
      </div>
    </div>
  `,
  styles: [`
    .hero-card {
      border: 1px solid var(--border-primary);
      background:
        radial-gradient(circle at top right, rgba(0, 212, 170, 0.18), transparent 45%),
        linear-gradient(160deg, rgba(15, 22, 35, 0.95), rgba(10, 15, 25, 0.92));
    }

    .hero-kicker {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }

    .quick-stats {
      margin-top: 1rem;
      display: grid;
      gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    }

    .quick-stat {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
      padding: 0.75rem;
      display: grid;
      gap: 0.15rem;
    }

    .quick-stat span {
      color: var(--text-muted);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .quick-stat strong {
      font-size: 1.28rem;
      color: var(--text-primary);
      font-family: var(--font-display);
    }

    .bar-chart {
      display: grid;
      gap: 0.55rem;
      margin-top: 0.8rem;
    }

    .bar-row {
      display: grid;
      grid-template-columns: 58px 1fr 24px;
      gap: 0.55rem;
      align-items: center;
    }

    .bar-label,
    .bar-value {
      color: var(--text-secondary);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .bar-track {
      height: 8px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 99px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      border-radius: 99px;
      background: linear-gradient(90deg, #00d4aa 0%, #1dd9a0 55%, #f59e0b 100%);
    }

    .status-grid {
      display: grid;
      gap: 0.65rem;
      margin-top: 0.8rem;
    }

    .status-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 0.65rem 0.75rem;
      color: var(--text-secondary);
    }

    .status-item strong {
      color: var(--text-primary);
      text-transform: capitalize;
      font-size: 0.83rem;
    }
  `],
})
export class DashboardComponent implements OnInit {
  liveMatches: Match[] = [];
  pipelineStatus: PipelineStatus | null = null;
  formatDistribution: Array<{ label: string; value: number }> = [];
  maxFormatValue = 0;
  loading = true;
  pipelineError = '';
  liveError = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getLiveMatches().subscribe({
      next: (response) => {
        this.liveMatches = response.results;
        this.setFormatDistribution(response.results);
        this.liveError = '';
      },
      error: () => {
        this.liveMatches = [];
        this.formatDistribution = [];
        this.maxFormatValue = 0;
        this.liveError = 'Live matches could not be loaded.';
      },
    });

    this.api.getPipelineStatus().subscribe({
      next: (status) => {
        this.pipelineStatus = status;
        this.loading = false;
        this.pipelineError = '';
      },
      error: () => {
        this.loading = false;
        this.pipelineError = 'Pipeline status is currently unavailable.';
      },
    });
  }

  barWidth(value: number, maxValue: number): number {
    if (!maxValue) {
      return 0;
    }
    return Math.max(8, (value / maxValue) * 100);
  }

  private setFormatDistribution(matches: Match[]): void {
    const counts = matches.reduce((acc, match) => {
      const key = (match.format || 'other').toUpperCase();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    this.formatDistribution = Object.entries(counts)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);

    this.maxFormatValue = this.formatDistribution.reduce((max, row) => Math.max(max, row.value), 0);
  }
}
