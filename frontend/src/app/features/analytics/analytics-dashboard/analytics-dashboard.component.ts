import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, TeamAnalytics, PlayerAnalytics } from '../../../core/services/api.service';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Analytics</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Team and player analytics explorer.</p>

        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.75rem;">
          <input class="input" [(ngModel)]="teamName" placeholder="Team name (e.g. India)" />
          <button class="btn btn-primary" (click)="loadTeamAnalytics()" [disabled]="teamLoading">
            {{ teamLoading ? 'Loading...' : 'Load Team' }}
          </button>
        </div>
        <p *ngIf="teamError" class="status-error" style="margin-top:.75rem;">{{ teamError }}</p>

        <div *ngIf="teamAnalytics" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
          <h3>Team Analytics</h3>
          <p><strong>Win Rate:</strong> {{ teamAnalytics.win_rate }}%</p>
          <p><strong>Losses:</strong> {{ teamAnalytics.losses }}</p>
          <p><strong>Total Matches:</strong> {{ teamAnalytics.matches_total }}</p>
        </div>

        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:1rem;">
          <input class="input" type="number" [(ngModel)]="playerId" placeholder="Player ID" />
          <button class="btn btn-secondary" (click)="loadPlayerAnalytics()" [disabled]="playerLoading">
            {{ playerLoading ? 'Loading...' : 'Load Player' }}
          </button>
        </div>
        <p *ngIf="playerError" class="status-error" style="margin-top:.75rem;">{{ playerError }}</p>

        <div *ngIf="playerAnalytics" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
          <h3>Player Analytics</h3>
          <p><strong>Matches:</strong> {{ playerAnalytics.matches_played }}</p>
          <p><strong>Total Runs:</strong> {{ playerAnalytics.total_runs }}</p>
          <p><strong>Total Wickets:</strong> {{ playerAnalytics.total_wickets }}</p>
        </div>
      </div>
    </div>
  `,
})
export class AnalyticsDashboardComponent {
  teamName = 'India';
  playerId: number | null = null;
  teamAnalytics: TeamAnalytics | null = null;
  playerAnalytics: PlayerAnalytics | null = null;
  teamLoading = false;
  playerLoading = false;
  teamError = '';
  playerError = '';

  constructor(private api: ApiService) {}

  loadTeamAnalytics(): void {
    if (!this.teamName.trim()) return;
    this.teamLoading = true;
    this.teamError = '';
    this.api.getTeamAnalytics(this.teamName.trim()).subscribe({
      next: (response) => {
        this.teamAnalytics = response;
        this.teamLoading = false;
      },
      error: () => {
        this.teamAnalytics = null;
        this.teamLoading = false;
        this.teamError = 'Team analytics unavailable for this input.';
      },
    });
  }

  loadPlayerAnalytics(): void {
    if (!this.playerId) return;
    this.playerLoading = true;
    this.playerError = '';
    this.api.getPlayerAnalytics(this.playerId).subscribe({
      next: (response) => {
        this.playerAnalytics = response;
        this.playerLoading = false;
      },
      error: () => {
        this.playerAnalytics = null;
        this.playerLoading = false;
        this.playerError = 'Player analytics unavailable for this ID.';
      },
    });
  }
}
