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
          <div *ngFor="let series of seriesList" style="padding:.75rem 0; border-bottom:1px solid var(--border);">
            <strong>{{ series.name }}</strong>
            <div class="text-secondary">ID: {{ series.id }}</div>
          </div>
          <p *ngIf="seriesList.length === 0" class="text-secondary">No series available.</p>
        </div>
      </div>
    </div>
  `,
})
export class SeriesListComponent implements OnInit {
  seriesList: Series[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getSeries().subscribe({
      next: (response) => {
        this.seriesList = response.results;
      },
      error: () => {
        this.seriesList = [];
      },
    });
  }
}
