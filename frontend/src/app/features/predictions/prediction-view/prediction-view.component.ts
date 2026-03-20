import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, PredictionJob } from '../../../core/services/api.service';

@Component({
  selector: 'app-prediction-view',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Prediction</h1>
        <p class="text-secondary" style="margin-top:0.5rem">
          Generate a pre-match prediction and inspect model output.
        </p>

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
    this.loading = true;
    this.error = '';

    this.api.createPrediction(this.matchId, 'pre_match').subscribe({
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
