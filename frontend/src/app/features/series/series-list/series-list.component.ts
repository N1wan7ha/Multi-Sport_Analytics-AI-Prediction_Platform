import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, Match, PipelineStatus, Series } from '../../../core/services/api.service';

interface HistoricSeriesCard {
  title: string;
  subtitle: string;
  matchCount: number;
  topTeams: string[];
}

@Component({
  selector: 'app-series-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Series</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Browse synced cricket series and latest season snapshots.</p>

        <div style="display:flex; gap:.55rem; align-items:center; flex-wrap:wrap; margin-top:.75rem;">
          <button class="btn btn-primary" (click)="refreshNow()" [disabled]="loading">Refresh Series</button>
          <p class="text-secondary" style="font-size:.8rem; margin:0;" *ngIf="pipelineStatus?.last_sync_unified_matches">
            Last pipeline sync: {{ pipelineStatus?.last_sync_unified_matches }}
          </p>
        </div>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading series...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>

          <div *ngIf="seriesList.length > 0">
            <div *ngFor="let series of seriesList" class="list-row">
              <a [routerLink]="['/series', series.id]"><strong>{{ series.name }}</strong></a>
              <div class="text-secondary">ID: {{ series.id }}</div>
            </div>
          </div>

          <div *ngIf="!loading && !error && seriesList.length === 0 && historicSeries.length > 0">
            <p class="text-secondary" style="margin-bottom:.6rem;">
              No synced series found. Showing latest season cards from match history.
            </p>
            <div *ngFor="let card of historicSeries" class="list-row" style="display:grid; gap:.3rem;">
              <strong>{{ card.title }}</strong>
              <div class="text-secondary">{{ card.subtitle }}</div>
              <div class="text-secondary">Matches: {{ card.matchCount }} · Teams: {{ card.topTeams.join(' · ') }}</div>
              <a routerLink="/history" class="btn btn-secondary" style="width:max-content;">Open History Explorer</a>
            </div>
          </div>

          <p *ngIf="!loading && !error && seriesList.length === 0 && historicSeries.length === 0" class="text-secondary">
            No series or historic matches available yet.
          </p>
        </div>
      </div>
    </div>
  `,
})
export class SeriesListComponent implements OnInit, OnDestroy {
  seriesList: Series[] = [];
  historicSeries: HistoricSeriesCard[] = [];
  pipelineStatus: PipelineStatus | null = null;
  loading = false;
  error = '';
  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.refreshNow();
    this.api.getPipelineStatus().subscribe({
      next: (response) => {
        this.pipelineStatus = response;
      },
      error: () => {
        this.pipelineStatus = null;
      },
    });

    this.refreshTimer = setInterval(() => {
      this.refreshNow();
    }, 60000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  refreshNow(): void {
    this.loading = true;
    this.error = '';
    this.api.getSeries().subscribe({
      next: (response) => {
        this.seriesList = response.results;
        if (this.seriesList.length > 0) {
          this.loading = false;
          return;
        }

        this.loadHistoricFallback();
      },
      error: () => {
        this.seriesList = [];
        this.loadHistoricFallback(true);
      },
    });
  }

  private loadHistoricFallback(loadFailed = false): void {
    this.api.getMatches({ status: 'complete' }).subscribe({
      next: (response) => {
        this.historicSeries = this.buildHistoricSeriesCards(response.results);
        this.loading = false;
        this.error = loadFailed && this.historicSeries.length === 0
          ? 'Unable to load series right now.'
          : '';
      },
      error: () => {
        this.historicSeries = [];
        this.loading = false;
        this.error = 'Unable to load series right now.';
      },
    });
  }

  private buildHistoricSeriesCards(matches: Match[]): HistoricSeriesCard[] {
    const grouped = new Map<string, Match[]>();

    for (const match of matches) {
      const year = (match.match_date || '').slice(0, 4) || 'Unknown';
      const category = (match.category || 'other').toLowerCase();
      const key = `${year}-${category}`;
      if (!grouped.has(key)) {
        grouped.set(key, []);
      }
      grouped.get(key)!.push(match);
    }

    return Array.from(grouped.entries())
      .map(([key, rows]) => {
        const [year, category] = key.split('-');
        const teams = new Map<string, number>();
        for (const row of rows) {
          const t1 = row.team1?.name || '';
          const t2 = row.team2?.name || '';
          if (t1) teams.set(t1, (teams.get(t1) || 0) + 1);
          if (t2) teams.set(t2, (teams.get(t2) || 0) + 1);
        }

        const topTeams = Array.from(teams.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 4)
          .map(([name]) => name);

        return {
          title: `${year} ${this.toTitleCase(category)} Series`,
          subtitle: `Historic ${this.toTitleCase(category)} season snapshot`,
          matchCount: rows.length,
          topTeams,
        };
      })
      .sort((a, b) => b.title.localeCompare(a.title))
      .slice(0, 10);
  }

  private toTitleCase(value: string): string {
    if (!value) return 'Unknown';
    return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
  }
}
