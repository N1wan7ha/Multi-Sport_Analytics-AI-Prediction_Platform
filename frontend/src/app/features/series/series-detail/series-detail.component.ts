import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Match } from '../../../core/services/api.service';

@Component({
  selector: 'app-series-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap;">
          <div>
            <h1>Series Detail</h1>
            <p class="text-secondary" style="margin-top:0.5rem;">
              Matches inside the selected series.
            </p>
          </div>
          <div style="display:flex; gap:.5rem; align-items:center;">
            <button class="btn btn-secondary" (click)="refreshNow()" [disabled]="loading">
              {{ loading ? 'Refreshing...' : 'Refresh Series' }}
            </button>
            <span class="text-secondary" style="font-size:.75rem;" *ngIf="lastUpdatedAt">
              Updated: {{ lastUpdatedAt }}
            </span>
          </div>
        </div>

        <div style="margin-top:1rem; display:flex; gap:.75rem; flex-wrap:wrap;">
          <a routerLink="/series" class="btn btn-secondary">Back to Series</a>
        </div>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading series matches...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>

          <div *ngFor="let match of matches" class="list-row">
            <a [routerLink]="['/matches', match.id]">
              <span style="display:inline-flex; align-items:center; gap:.38rem;">
                <img
                  *ngIf="match.team1?.logo_url"
                  [src]="match.team1?.logo_url"
                  [alt]="match.team1?.name + ' logo'"
                  style="width:18px; height:18px; border-radius:50%; object-fit:cover; border:1px solid var(--border-primary);"
                />
                <strong>{{ match.team1?.name || 'Unknown' }}</strong>
                <span>vs</span>
                <img
                  *ngIf="match.team2?.logo_url"
                  [src]="match.team2?.logo_url"
                  [alt]="match.team2?.name + ' logo'"
                  style="width:18px; height:18px; border-radius:50%; object-fit:cover; border:1px solid var(--border-primary);"
                />
                <strong>{{ match.team2?.name || 'Unknown' }}</strong>
              </span>
            </a>
            <div class="text-secondary">
              {{ match.format | uppercase }} · {{ match.status }} · {{ match.match_date }}
            </div>
          </div>

          <p *ngIf="!loading && !error && matches.length === 0" class="text-secondary">
            No matches found for this series.
          </p>
        </div>
      </div>
    </div>
  `,
})
export class SeriesDetailComponent implements OnInit, OnDestroy {
  seriesId = 0;
  matches: Match[] = [];
  loading = false;
  error = '';
  lastUpdatedAt = '';
  private autoRefreshTimer: any;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    this.seriesId = Number(this.route.snapshot.paramMap.get('id') || 0);
    if (!this.seriesId) {
      this.error = 'Invalid series id.';
      return;
    }

    this.loadSeriesMatches();

    // Auto-refresh every 60 seconds
    this.autoRefreshTimer = setInterval(() => {
      this.loadSeriesMatches();
    }, 60000);
  }

  ngOnDestroy(): void {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer);
    }
  }

  public refreshNow(): void {
    this.loadSeriesMatches();
  }

  private loadSeriesMatches(): void {
    this.loading = true;
    this.error = '';

    this.api.getSeriesMatches(this.seriesId).subscribe({
      next: (response) => {
        this.matches = response.results;
        this.loading = false;
        this.updateTimestamp();
      },
      error: () => {
        this.matches = [];
        this.loading = false;
        this.error = 'Unable to load series matches right now.';
      },
    });
  }

  private updateTimestamp(): void {
    const now = new Date();
    this.lastUpdatedAt = now.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }
}
