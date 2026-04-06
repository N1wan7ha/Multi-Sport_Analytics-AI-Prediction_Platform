import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, Match } from '../../../core/services/api.service';

@Component({
  selector: 'app-history-explorer',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card" style="margin-bottom:1rem;">
        <h1>History Explorer</h1>
        <p class="text-secondary" style="margin-top:.5rem;">
          Explore historical matches by team, format, venue, and season.
        </p>

        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.65rem; margin-top:1rem;">
          <input class="input" [(ngModel)]="filters.team" placeholder="Team (e.g. India)" />
          <select class="input" [(ngModel)]="filters.format">
            <option value="">Any Format</option>
            <option value="test">Test</option>
            <option value="odi">ODI</option>
            <option value="t20">T20</option>
            <option value="t10">T10</option>
          </select>
          <select class="input" [(ngModel)]="filters.category">
            <option value="">Any Type</option>
            <option value="international">International</option>
            <option value="franchise">Franchise</option>
            <option value="domestic">Domestic</option>
          </select>
          <input class="input" [(ngModel)]="filters.venue" placeholder="Venue (e.g. Lord's)" />
          <input class="input" [(ngModel)]="filters.season" placeholder="Season year (e.g. 2023)" />
        </div>

        <div style="display:flex; gap:.55rem; margin-top:.8rem; flex-wrap:wrap;">
          <button class="btn btn-primary" (click)="loadHistory()">Apply Filters</button>
          <button class="btn btn-secondary" (click)="clearFilters()">Reset</button>
          <span class="text-secondary" style="align-self:center;">{{ total }} matches found</span>
        </div>
      </div>

      <div class="card">
        <h3>Historical Matches</h3>
        <p *ngIf="loading" class="text-secondary" style="margin-top:.5rem;">Loading history...</p>
        <p *ngIf="error" class="status-error" style="margin-top:.5rem;">{{ error }}</p>

        <div *ngIf="!loading && !error" style="margin-top:.75rem; display:grid; gap:.6rem;">
          <div *ngFor="let match of matches" class="list-row" style="display:grid; grid-template-columns:1fr auto; gap:.75rem;">
            <div>
              <a [routerLink]="['/matches', match.id]" style="font-weight:600;">
                {{ match.team1?.name || 'Unknown' }} vs {{ match.team2?.name || 'Unknown' }}
              </a>
              <div class="text-secondary" style="font-size:.85rem; margin-top:.2rem;">
                {{ match.format | uppercase }} · {{ match.match_date }} · {{ match.venue?.name || 'Venue TBD' }}
              </div>
              <div class="text-secondary" style="font-size:.82rem; margin-top:.2rem;" *ngIf="match.result_text">
                Result: {{ match.result_text }}
              </div>
            </div>
            <div style="display:flex; align-items:center;">
              <span class="badge badge--complete">{{ match.status }}</span>
            </div>
          </div>

          <p *ngIf="matches.length === 0" class="text-secondary">No matches found for current filters.</p>
        </div>
      </div>
    </div>
  `,
})
export class HistoryExplorerComponent implements OnInit {
  matches: Match[] = [];
  total = 0;
  loading = false;
  error = '';

  filters: { team: string; format: string; category: string; venue: string; season: string } = {
    team: '',
    format: '',
    category: '',
    venue: '',
    season: '',
  };

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.loading = true;
    this.error = '';

    this.api.getMatches({
      status: 'complete',
      team: this.filters.team.trim() || undefined,
      format: this.filters.format || undefined,
      category: this.filters.category || undefined,
      venue: this.filters.venue.trim() || undefined,
      season: this.filters.season.trim() || undefined,
    }).subscribe({
      next: (res) => {
        this.matches = res.results;
        this.total = res.count;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.matches = [];
        this.total = 0;
        this.error = 'Unable to load historical matches.';
      },
    });
  }

  clearFilters(): void {
    this.filters = { team: '', format: '', category: '', venue: '', season: '' };
    this.loadHistory();
  }
}
