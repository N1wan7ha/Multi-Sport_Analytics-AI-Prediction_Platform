import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Match, PredictionJob } from '../../../core/services/api.service';

@Component({
  selector: 'app-match-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Match Detail</h1>
        <p *ngIf="!match" class="text-secondary" style="margin-top:0.5rem">Loading match...</p>

        <div *ngIf="match" style="margin-top:.5rem;">
          <h2 style="margin-bottom:.25rem;">{{ match.team1.name }} vs {{ match.team2.name }}</h2>
          <p class="text-secondary">{{ match.format | uppercase }} · {{ match.status }} · {{ match.match_date }}</p>
          <p *ngIf="match.venue" class="text-secondary">Venue: {{ match.venue.name }}, {{ match.venue.city }}</p>
          <a [routerLink]="['/matches', match.id, 'predict']" class="btn btn-primary" style="margin-top:.5rem;">Run Prediction</a>
        </div>

        <div style="margin-top:1rem;" *ngIf="latestPrediction?.result as result">
          <h3>Latest Prediction</h3>
          <p><strong>{{ result.team1.name }}:</strong> {{ (result.team1_win_probability * 100) | number:'1.0-2' }}%</p>
          <p><strong>{{ result.team2.name }}:</strong> {{ (result.team2_win_probability * 100) | number:'1.0-2' }}%</p>
          <p class="text-secondary">Confidence: {{ result.confidence_score }}</p>
        </div>
      </div>
    </div>
  `,
})
export class MatchDetailComponent implements OnInit {
  match: Match | null = null;
  latestPrediction: PredictionJob | null = null;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) return;

    this.api.getMatch(id).subscribe({
      next: (response) => {
        this.match = response;
      },
    });

    this.api.getLatestPredictionForMatch(id).subscribe({
      next: (response) => {
        this.latestPrediction = response;
      },
      error: () => {
        this.latestPrediction = null;
      },
    });
  }
}
