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
      <div class="card" style="margin-bottom: 1rem;">
        <h1>Dashboard</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Live data and pipeline health overview.
        </p>
      </div>

      <div class="grid" style="display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(260px,1fr));">
        <div class="card">
          <h3>Pipeline</h3>
          <p *ngIf="loading" class="text-secondary">Loading status...</p>
          <p *ngIf="!loading && pipelineError" class="status-error">{{ pipelineError }}</p>
          <div *ngIf="!loading && pipelineStatus">
            <p><strong>Current matches:</strong> {{ pipelineStatus.count_current_matches }}</p>
            <p><strong>Live feed rows:</strong> {{ pipelineStatus.count_cricbuzz_live }}</p>
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
      </div>

      <div style="margin-top:1rem; display:flex; gap:.75rem; flex-wrap:wrap;">
        <a routerLink="/matches" class="btn btn-primary">Browse Matches</a>
        <a routerLink="/players" class="btn btn-secondary">Browse Players</a>
      </div>
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  liveMatches: Match[] = [];
  pipelineStatus: PipelineStatus | null = null;
  loading = true;
  pipelineError = '';
  liveError = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getLiveMatches().subscribe({
      next: (response) => {
        this.liveMatches = response.results;
        this.liveError = '';
      },
      error: () => {
        this.liveMatches = [];
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
}
