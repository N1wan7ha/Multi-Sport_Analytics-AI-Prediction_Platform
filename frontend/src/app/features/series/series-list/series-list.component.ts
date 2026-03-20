import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, Series } from '../../../core/services/api.service';

@Component({
  selector: 'app-series-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Series</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Browse synced cricket series.</p>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading series...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>

          <div *ngFor="let series of seriesList" class="list-row">
            <a [routerLink]="['/series', series.id]"><strong>{{ series.name }}</strong></a>
            <div class="text-secondary">ID: {{ series.id }}</div>
          </div>
          <p *ngIf="!loading && !error && seriesList.length === 0" class="text-secondary">No series available.</p>
        </div>
      </div>
    </div>
  `,
})
export class SeriesListComponent implements OnInit {
  seriesList: Series[] = [];
  loading = false;
  error = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loading = true;
    this.error = '';
    this.api.getSeries().subscribe({
      next: (response) => {
        this.seriesList = response.results;
        this.loading = false;
      },
      error: () => {
        this.seriesList = [];
        this.loading = false;
        this.error = 'Unable to load series right now.';
      },
    });
  }
}
