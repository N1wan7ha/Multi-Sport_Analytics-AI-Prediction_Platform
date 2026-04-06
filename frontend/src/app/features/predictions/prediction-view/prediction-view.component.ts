import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, PredictionJob } from '../../../core/services/api.service';

@Component({
  selector: 'app-prediction-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Prediction</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Generate pre-match or live predictions and inspect model output.
        </p>

        <div style="margin-top:1rem; display:flex; gap:.5rem; flex-wrap:wrap;">
          <button class="btn" [class.btn-primary]="predictionType === 'pre_match'" [class.btn-secondary]="predictionType !== 'pre_match'" (click)="setPredictionType('pre_match')">
            Pre-Match
          </button>
          <button class="btn" [class.btn-primary]="predictionType === 'live'" [class.btn-secondary]="predictionType !== 'live'" (click)="setPredictionType('live')">
            Live
          </button>
        </div>

        <div *ngIf="predictionType === 'live'" style="margin-top:1rem; display:grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap:.75rem;">
          <label>
            <span class="text-secondary" style="display:block; margin-bottom:.25rem;">Current Over</span>
            <input class="input" type="number" min="0" [(ngModel)]="currentOver" placeholder="e.g. 14" />
          </label>
          <label>
            <span class="text-secondary" style="display:block; margin-bottom:.25rem;">Current Score</span>
            <input class="input" type="text" [(ngModel)]="currentScore" placeholder="e.g. 122/3" />
          </label>
        </div>

        <div style="margin-top:1rem; display:flex; gap:.75rem; flex-wrap:wrap;">
          <button class="btn btn-primary" [disabled]="loading || !matchId" (click)="runPrediction()">
            {{ loading ? 'Submitting...' : 'Run Prediction' }}
          </button>
          <a [routerLink]="['/matches', matchId]" class="btn btn-secondary">Back To Match</a>
        </div>

        <p *ngIf="error" style="margin-top:1rem; color:#d83a52;">{{ error }}</p>

        <div *ngIf="job" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
          <p><strong>Job:</strong> #{{ job.id }} · <strong>Status:</strong> {{ job.status }}</p>
          <p *ngIf="job.status === 'processing' || job.status === 'pending'" class="text-secondary">
            Polling result every 2 seconds...
          </p>
          <p *ngIf="job.status === 'failed'" class="status-error">
            Prediction failed. Please retry or check backend logs.
          </p>

          <div *ngIf="job.result" style="margin-top:.75rem;">
            <h3>Result</h3>
            <p><strong>{{ job.result.team1.name }}:</strong> {{ (job.result.team1_win_probability * 100) | number:'1.0-2' }}%</p>
            <p><strong>{{ job.result.team2.name }}:</strong> {{ (job.result.team2_win_probability * 100) | number:'1.0-2' }}%</p>
            <p><strong>Confidence:</strong> {{ job.result.confidence_score }}</p>
            <p *ngIf="job.result.current_over !== null && job.result.current_over !== undefined">
              <strong>Live:</strong> Over {{ job.result.current_over }} · Score {{ job.result.current_score || '-' }}
            </p>
            <p class="text-secondary"><strong>Model:</strong> {{ job.result.feature_snapshot['model_kind'] || 'unknown' }}</p>

            <div *ngIf="job.result.pre_match_projection as projection" style="margin-top:.95rem; border-top:1px dashed var(--border); padding-top:.8rem;">
              <h4 style="margin:0 0 .5rem;">Pre-Match Forecast</h4>
              <p *ngIf="projection.gender_segment" class="text-secondary" style="margin-top:.2rem;">
                <strong>Division:</strong> {{ projection.gender_segment === 'women' ? 'Women' : 'Men' }}
              </p>
              <p *ngIf="projection.projected_winner">
                <strong>Projected Winner:</strong>
                {{ projection.projected_winner.team_name }}
                ({{ (projection.projected_winner.win_probability * 100) | number:'1.0-2' }}%)
              </p>

              <div *ngIf="projection.team_totals as totals" style="display:grid; gap:.45rem; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); margin-top:.4rem;">
                <div *ngIf="totals.team1" class="list-row" style="display:grid; gap:.2rem;">
                  <strong>{{ totals.team1.team_name }}</strong>
                  <span class="text-secondary">
                    Score: {{ totals.team1.projected_score }}
                    ({{ totals.team1.projected_score_range[0] }}-{{ totals.team1.projected_score_range[1] }})
                  </span>
                  <span class="text-secondary">Wickets: {{ totals.team1.projected_wickets_lost }}</span>
                </div>
                <div *ngIf="totals.team2" class="list-row" style="display:grid; gap:.2rem;">
                  <strong>{{ totals.team2.team_name }}</strong>
                  <span class="text-secondary">
                    Score: {{ totals.team2.projected_score }}
                    ({{ totals.team2.projected_score_range[0] }}-{{ totals.team2.projected_score_range[1] }})
                  </span>
                  <span class="text-secondary">Wickets: {{ totals.team2.projected_wickets_lost }}</span>
                </div>
              </div>

              <div *ngIf="projection.top_performers as tp" style="margin-top:.6rem; display:grid; gap:.25rem;">
                <p *ngIf="tp.top_batter"><strong>Top Batter:</strong> {{ tp.top_batter.player_name }} ({{ tp.top_batter.team_name }})</p>
                <p *ngIf="tp.best_bowler"><strong>Best Bowler:</strong> {{ tp.best_bowler.player_name }} ({{ tp.best_bowler.team_name }})</p>
                <p *ngIf="tp.best_all_rounder"><strong>Best All-Rounder:</strong> {{ tp.best_all_rounder.player_name }} ({{ tp.best_all_rounder.team_name }})</p>
              </div>

              <p *ngIf="projection.insights?.length" class="text-secondary" style="margin-top:.5rem;">
                {{ (projection.insights || [])[0] }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class PredictionViewComponent implements OnInit, OnDestroy {
  matchId = 0;
  job: PredictionJob | null = null;
  loading = false;
  error = '';
  predictionType: 'pre_match' | 'live' = 'pre_match';
  currentOver: number | null = null;
  currentScore = '';
  private pollId: ReturnType<typeof setInterval> | null = null;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    this.matchId = Number(this.route.snapshot.paramMap.get('id') || 0);
  }

  ngOnDestroy(): void {
    if (this.pollId) {
      clearInterval(this.pollId);
      this.pollId = null;
    }
  }

  runPrediction(): void {
    if (!this.matchId || this.loading) return;
    if (this.predictionType === 'live' && (this.currentOver === null || this.currentOver < 0)) {
      this.error = 'Current over is required for live predictions.';
      return;
    }

    this.loading = true;
    this.error = '';

    this.api.createPrediction(
      this.matchId,
      this.predictionType,
      this.predictionType === 'live' && this.currentOver !== null
        ? { current_over: this.currentOver, current_score: this.currentScore || '' }
        : undefined
    ).subscribe({
      next: (created) => {
        this.job = created;
        this.loading = false;
        this.startPolling(created.id);
      },
      error: () => {
        this.loading = false;
        this.error = 'Prediction request failed. Please login and try again.';
      },
    });
  }

  setPredictionType(type: 'pre_match' | 'live'): void {
    this.predictionType = type;
    this.error = '';
  }

  private startPolling(jobId: number): void {
    if (this.pollId) {
      clearInterval(this.pollId);
    }

    this.pollId = setInterval(() => {
      this.api.getPrediction(jobId).subscribe({
        next: (current) => {
          this.job = current;
          if (current.status === 'complete' || current.status === 'failed') {
            if (this.pollId) {
              clearInterval(this.pollId);
              this.pollId = null;
            }
          }
        },
      });
    }, 2000);
  }
}
