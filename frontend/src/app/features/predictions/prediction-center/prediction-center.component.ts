import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Match, PredictionJob } from '../../../core/services/api.service';

@Component({
  selector: 'app-prediction-center',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>AI Predictions Hub</h1>
        <p class="text-secondary" style="margin-top:0.5rem;">
          Pick a match, choose mode, run prediction, and read confidence instantly.
        </p>

        <div style="margin-top:.9rem; display:grid; gap:.6rem; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));">
          <div class="list-row" style="display:grid; gap:.2rem;">
            <strong>1. Select Match</strong>
            <span class="text-secondary">Use quick pick cards or dropdown.</span>
          </div>
          <div class="list-row" style="display:grid; gap:.2rem;">
            <strong>2. Choose Mode</strong>
            <span class="text-secondary">Pre-match or live context input.</span>
          </div>
          <div class="list-row" style="display:grid; gap:.2rem;">
            <strong>3. Run & Compare</strong>
            <span class="text-secondary">See win probabilities and confidence.</span>
          </div>
        </div>

        <div style="margin-top:1rem; display:flex; gap:.5rem; flex-wrap:wrap;">
          <button class="btn" [class.btn-primary]="predictionType === 'pre_match'" [class.btn-secondary]="predictionType !== 'pre_match'" (click)="setPredictionType('pre_match')">
            Pre-Match
          </button>
          <button class="btn" [class.btn-primary]="predictionType === 'live'" [class.btn-secondary]="predictionType !== 'live'" (click)="setPredictionType('live')">
            Live
          </button>
          <button class="btn btn-secondary" (click)="loadMatches()">Refresh Matches</button>
        </div>

        <div style="margin-top:.75rem; display:flex; gap:.5rem; flex-wrap:wrap; align-items:center;">
          <span class="text-secondary">Division:</span>
          <button class="btn" [class.btn-primary]="genderFilter === 'all'" [class.btn-secondary]="genderFilter !== 'all'" (click)="setGenderFilter('all')">
            All ({{ matches.length }})
          </button>
          <button class="btn" [class.btn-primary]="genderFilter === 'men'" [class.btn-secondary]="genderFilter !== 'men'" (click)="setGenderFilter('men')">
            Men ({{ menCount }})
          </button>
          <button class="btn" [class.btn-primary]="genderFilter === 'women'" [class.btn-secondary]="genderFilter !== 'women'" (click)="setGenderFilter('women')">
            Women ({{ womenCount }})
          </button>
        </div>

        <div style="margin-top:1rem;">
          <p class="text-secondary" style="margin-bottom:.45rem;">Quick picks</p>
          <div style="display:grid; gap:.5rem; grid-template-columns:repeat(auto-fit,minmax(260px,1fr));">
            <button
              *ngFor="let match of filteredMatches.slice(0, 6)"
              class="list-row"
              style="text-align:left; cursor:pointer; background:transparent;"
              (click)="selectedMatchId = match.id"
            >
              <strong>{{ match.team1?.name || 'Unknown' }} vs {{ match.team2?.name || 'Unknown' }}</strong>
              <span class="text-secondary">{{ match.format | uppercase }} · {{ match.status }} · {{ match.match_date }}</span>
            </button>
          </div>
        </div>

        <div style="margin-top:1rem; display:grid; gap:.6rem;">
          <label>
            <span class="text-secondary" style="display:block; margin-bottom:.25rem;">Select Match</span>
            <select class="input" [(ngModel)]="selectedMatchId">
              <option [ngValue]="0">Choose a match...</option>
              <option *ngFor="let match of filteredMatches" [ngValue]="match.id">
                {{ match.team1?.name || 'Unknown' }} vs {{ match.team2?.name || 'Unknown' }} · {{ match.format | uppercase }} · {{ match.status }}
              </option>
            </select>
          </label>
        </div>

        <div *ngIf="predictionType === 'live'" style="margin-top:1rem; display:grid; grid-template-columns: repeat(auto-fit,minmax(170px,1fr)); gap:.75rem;">
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
          <button class="btn btn-primary" [disabled]="loading || !selectedMatchId" (click)="runPrediction()">
            {{ loading ? 'Submitting...' : 'Run AI Prediction' }}
          </button>
          <a *ngIf="selectedMatchId" [routerLink]="['/matches', selectedMatchId]" class="btn btn-secondary">Open Match</a>
        </div>

        <p *ngIf="error" class="status-error" style="margin-top:1rem;">{{ error }}</p>

        <div *ngIf="job" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
          <p><strong>Job:</strong> #{{ job.id }} · <strong>Status:</strong> {{ job.status }}</p>
          <p *ngIf="job.status === 'processing' || job.status === 'pending'" class="text-secondary">
            Processing prediction... refreshing every 2 seconds.
          </p>
          <p *ngIf="job.status === 'failed'" class="status-error">Prediction failed. Please retry.</p>

          <div *ngIf="job.result" style="margin-top:.75rem;">
            <h3>Prediction Result</h3>
            <p><strong>{{ job.result.team1.name }}:</strong> {{ (job.result.team1_win_probability * 100) | number:'1.0-2' }}%</p>
            <div style="height:8px; border-radius:999px; background:rgba(255,255,255,0.08); overflow:hidden; margin:.35rem 0 .55rem;">
              <div style="height:100%; background:linear-gradient(90deg,#00d4aa,#1dd9a0);" [style.width.%]="job.result.team1_win_probability * 100"></div>
            </div>
            <p><strong>{{ job.result.team2.name }}:</strong> {{ (job.result.team2_win_probability * 100) | number:'1.0-2' }}%</p>
            <div style="height:8px; border-radius:999px; background:rgba(255,255,255,0.08); overflow:hidden; margin:.35rem 0 .55rem;">
              <div style="height:100%; background:linear-gradient(90deg,#22c55e,#f59e0b);" [style.width.%]="job.result.team2_win_probability * 100"></div>
            </div>
            <p><strong>Confidence:</strong> {{ job.result.confidence_score }}</p>
            <p *ngIf="job.result.current_over !== null && job.result.current_over !== undefined">
              <strong>Live Context:</strong> Over {{ job.result.current_over }} · Score {{ job.result.current_score || '-' }}
            </p>

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
export class PredictionCenterComponent implements OnInit, OnDestroy {
  matches: Match[] = [];
  genderFilter: 'all' | 'men' | 'women' = 'all';
  selectedMatchId = 0;
  predictionType: 'pre_match' | 'live' = 'pre_match';
  currentOver: number | null = null;
  currentScore = '';
  loading = false;
  error = '';
  job: PredictionJob | null = null;
  private pollId: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadMatches();
  }

  ngOnDestroy(): void {
    if (this.pollId) {
      clearInterval(this.pollId);
      this.pollId = null;
    }
  }

  setPredictionType(type: 'pre_match' | 'live'): void {
    this.predictionType = type;
    this.error = '';
  }

  setGenderFilter(filter: 'all' | 'men' | 'women'): void {
    this.genderFilter = filter;
    if (!this.filteredMatches.some((match) => match.id === this.selectedMatchId)) {
      this.selectedMatchId = 0;
    }
  }

  get filteredMatches(): Match[] {
    if (this.genderFilter === 'all') {
      return this.matches;
    }
    return this.matches.filter((match) => this.inferGenderBucket(match) === this.genderFilter);
  }

  get womenCount(): number {
    return this.matches.filter((match) => this.inferGenderBucket(match) === 'women').length;
  }

  get menCount(): number {
    return this.matches.filter((match) => this.inferGenderBucket(match) === 'men').length;
  }

  loadMatches(): void {
    this.error = '';
    this.api.getMatches({ status: 'upcoming' }).subscribe({
      next: (upcoming) => {
        this.api.getMatches({ status: 'live' }).subscribe({
          next: (live) => {
            const byId = new Map<number, Match>();
            [...live.results, ...upcoming.results].forEach((match) => byId.set(match.id, match));
            this.matches = Array.from(byId.values());
          },
          error: () => {
            this.matches = upcoming.results;
          },
        });
      },
      error: () => {
        this.matches = [];
        this.error = 'Unable to load matches for prediction.';
      },
    });
  }

  runPrediction(): void {
    if (!this.selectedMatchId || this.loading) return;
    if (this.predictionType === 'live' && (this.currentOver === null || this.currentOver < 0)) {
      this.error = 'Current over is required for live predictions.';
      return;
    }

    this.loading = true;
    this.error = '';

    this.api.createPrediction(
      this.selectedMatchId,
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

  private inferGenderBucket(match: Match): 'men' | 'women' {
    const combined = [
      match.name || '',
      match.team1?.name || '',
      match.team2?.name || '',
    ].join(' ');

    const isWomen = /\bwomen\b|\bwomen's\b|\bladies\b|\bgirls\b|\b[a-z]{2,6}-w\b|\b[a-z]{2,6}w\b|\(w\)/i.test(combined);
    return isWomen ? 'women' : 'men';
  }
}
