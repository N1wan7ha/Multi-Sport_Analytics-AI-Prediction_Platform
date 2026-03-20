import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Match, PredictionJob } from '../../../core/services/api.service';
import { LivePredictionSocketService } from '../../../core/services/live-prediction-socket.service';

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
            <div *ngIf="match.status === 'live'" class="text-secondary" style="margin-top:.3rem; font-size:.92rem;">
              <ng-container *ngIf="livePredictionByMatchId[match.id]?.result as result; else waitingLivePrediction">
                Live pred: {{ result.team1.name }} {{ (result.team1_win_probability * 100) | number:'1.0-1' }}%
                · {{ result.team2.name }} {{ (result.team2_win_probability * 100) | number:'1.0-1' }}%
              </ng-container>
              <ng-template #waitingLivePrediction>Live pred: waiting for latest model output...</ng-template>
            </div>
          </div>
          <p *ngIf="!loading && !error && matches.length === 0" class="text-secondary">No matches found.</p>
        </div>
      </div>
    </div>
  `,
})
export class MatchListComponent implements OnInit, OnDestroy {
  matches: Match[] = [];
  status = '';
  format = '';
  loading = false;
  error = '';
  livePredictionByMatchId: Record<number, PredictionJob | null> = {};
  liveSocketConnectedByMatchId: Record<number, boolean> = {};
  private liveRefreshInterval: ReturnType<typeof setInterval> | null = null;
  private activeLiveMatchIds: number[] = [];
  private liveSocketCleanupByMatchId: Record<number, () => void> = {};

  constructor(private api: ApiService, private liveSocket: LivePredictionSocketService) {}

  ngOnInit(): void {
    this.load();
  }

  ngOnDestroy(): void {
    this.stopLiveRefresh();
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
        this.syncLivePredictionRefresh();
        this.loading = false;
      },
      error: () => {
        this.matches = [];
        this.stopLiveRefresh();
        this.loading = false;
        this.error = 'Unable to load matches right now.';
      },
    });
  }

  private syncLivePredictionRefresh(): void {
    this.activeLiveMatchIds = this.matches.filter((match) => match.status === 'live').map((match) => match.id);
    const activeSet = new Set(this.activeLiveMatchIds);

    for (const key of Object.keys(this.liveSocketCleanupByMatchId)) {
      const matchId = Number(key);
      if (!activeSet.has(matchId)) {
        this.liveSocketCleanupByMatchId[matchId]?.();
        delete this.liveSocketCleanupByMatchId[matchId];
        delete this.liveSocketConnectedByMatchId[matchId];
      }
    }

    if (this.activeLiveMatchIds.length === 0) {
      this.livePredictionByMatchId = {};
      this.stopLiveRefresh();
      return;
    }

    for (const matchId of this.activeLiveMatchIds) {
      if (!this.liveSocketCleanupByMatchId[matchId]) {
        this.liveSocketCleanupByMatchId[matchId] = this.liveSocket.subscribeToMatch(matchId, {
          onOpen: () => {
            this.liveSocketConnectedByMatchId[matchId] = true;
          },
          onClose: () => {
            this.liveSocketConnectedByMatchId[matchId] = false;
          },
          onError: () => {
            this.liveSocketConnectedByMatchId[matchId] = false;
          },
          onPrediction: (prediction) => {
            this.liveSocketConnectedByMatchId[matchId] = true;
            this.livePredictionByMatchId[matchId] = prediction;
          },
        });
      }
    }

    this.refreshLivePredictions();
    if (!this.liveRefreshInterval) {
      this.liveRefreshInterval = setInterval(() => {
        this.refreshLivePredictions();
      }, 15000);
    }
  }

  private refreshLivePredictions(): void {
    for (const matchId of this.activeLiveMatchIds) {
      if (this.liveSocketConnectedByMatchId[matchId]) {
        continue;
      }
      this.api.getLatestPredictionForMatch(matchId, 'live').subscribe({
        next: (prediction) => {
          this.livePredictionByMatchId[matchId] = prediction;
        },
        error: () => {
          this.livePredictionByMatchId[matchId] = null;
        },
      });
    }
  }

  private stopLiveRefresh(): void {
    if (this.liveRefreshInterval) {
      clearInterval(this.liveRefreshInterval);
      this.liveRefreshInterval = null;
    }
    for (const key of Object.keys(this.liveSocketCleanupByMatchId)) {
      const matchId = Number(key);
      this.liveSocketCleanupByMatchId[matchId]?.();
      delete this.liveSocketCleanupByMatchId[matchId];
      delete this.liveSocketConnectedByMatchId[matchId];
    }
    this.activeLiveMatchIds = [];
  }
}
