import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Match } from '../../../core/services/api.service';

@Component({
  selector: 'app-match-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Matches</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Filter and browse matches.</p>
        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.75rem;">
          <select [(ngModel)]="status" (change)="load()" class="input">
            <option value="">All status</option>
            <option value="upcoming">Upcoming</option>
            <option value="live">Live</option>
            <option value="complete">Complete</option>
          </select>
          <select [(ngModel)]="format" (change)="load()" class="input">
            <option value="">All formats</option>
            <option value="test">Test</option>
            <option value="odi">ODI</option>
            <option value="t20">T20</option>
          </select>
        </div>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading matches...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>
          <div *ngFor="let match of matches" class="list-row">
            <a [routerLink]="['/matches', match.id]">
              <strong>{{ match.team1.name }}</strong> vs <strong>{{ match.team2.name }}</strong>
            </a>
            <div class="text-secondary">
              <span class="badge badge--{{ match.status === 'live' ? 'live' : (match.status === 'complete' ? 'complete' : 'upcoming') }}">{{ match.status }}</span>
              · {{ match.format | uppercase }}
            </div>
          </div>
          <p *ngIf="!loading && !error && matches.length === 0" class="text-secondary">No matches found.</p>
        </div>
      </div>
    </div>
  `,
})
export class MatchListComponent implements OnInit {
  matches: Match[] = [];
  status = '';
  format = '';
  loading = false;
  error = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';
    const filters: { status?: string; format?: string } = {};
    if (this.status) filters.status = this.status;
    if (this.format) filters.format = this.format;

    this.api.getMatches(filters).subscribe({
      next: (response) => {
        this.matches = response.results;
        this.loading = false;
      },
      error: () => {
        this.matches = [];
        this.loading = false;
        this.error = 'Unable to load matches right now.';
      },
    });
  }
}
