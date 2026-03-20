import { Component, OnInit } from '@angular/core';
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
        <h1>Series Detail</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Matches inside the selected series.
        </p>

        <div style="margin-top:1rem; display:flex; gap:.75rem; flex-wrap:wrap;">
          <a routerLink="/series" class="btn btn-secondary">Back to Series</a>
        </div>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading series matches...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>

          <div *ngFor="let match of matches" class="list-row">
            <a [routerLink]="['/matches', match.id]">
              <strong>{{ match.team1.name }}</strong> vs <strong>{{ match.team2.name }}</strong>
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
export class SeriesDetailComponent implements OnInit {
  seriesId = 0;
  matches: Match[] = [];
  loading = false;
  error = '';

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    this.seriesId = Number(this.route.snapshot.paramMap.get('id') || 0);
    if (!this.seriesId) {
      this.error = 'Invalid series id.';
      return;
    }

    this.loadSeriesMatches();
  }

  private loadSeriesMatches(): void {
    this.loading = true;
    this.error = '';

    this.api.getSeriesMatches(this.seriesId).subscribe({
      next: (response) => {
        this.matches = response.results;
        this.loading = false;
      },
      error: () => {
        this.matches = [];
        this.loading = false;
        this.error = 'Unable to load series matches right now.';
      },
    });
  }
}
