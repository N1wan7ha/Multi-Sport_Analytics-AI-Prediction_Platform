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
