import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Player, PlayerAnalytics } from '../../../core/services/api.service';

@Component({
  selector: 'app-player-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap;">
          <h1>Player</h1>
          <div style="display:flex; gap:.5rem; align-items:center;">
            <button class="btn btn-secondary" (click)="refreshNow()" [disabled]="loading">
              {{ loading ? 'Refreshing...' : 'Refresh' }}
            </button>
            <span class="text-secondary" style="font-size:.75rem;" *ngIf="lastUpdatedAt">
              Last updated: {{ lastUpdatedAt }}
            </span>
          </div>
        </div>

        <p *ngIf="!player" class="text-secondary" style="margin-top:0.5rem">Loading player profile...</p>

        <div *ngIf="player" style="margin-top:.5rem;">
          <h2 style="margin-bottom:.25rem;">{{ player.name }}</h2>
          <p class="text-secondary">{{ player.country }} · {{ player.role }}</p>
          <p class="text-secondary" *ngIf="player.team">Team: {{ player.team.name }}</p>
        </div>

        <div *ngIf="analytics" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
          <h3>Player Analytics</h3>
          <p><strong>Matches:</strong> {{ analytics.matches_played }}</p>
          <p><strong>Total Runs:</strong> {{ analytics.total_runs }}</p>
          <p><strong>Total Wickets:</strong> {{ analytics.total_wickets }}</p>
          <p class="text-secondary" *ngIf="analytics.batting_average !== undefined">Batting Average: {{ analytics.batting_average }}</p>
          <p class="text-secondary" *ngIf="analytics.avg_runs !== undefined">Avg Runs: {{ analytics.avg_runs }}</p>
          <p class="text-secondary" *ngIf="analytics.avg_wickets !== undefined">Avg Wickets: {{ analytics.avg_wickets }}</p>
        </div>

        <div *ngIf="player?.recent_stats?.length" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem;">
          <h3>Recent Innings Stats</h3>
          <div style="overflow:auto; margin-top:.55rem;">
            <table style="width:100%; border-collapse:collapse; font-size:.9rem;">
              <thead>
                <tr style="text-align:left; border-bottom:1px solid var(--border);">
                  <th style="padding:.45rem;">Match</th>
                  <th style="padding:.45rem;">Date</th>
                  <th style="padding:.45rem;">Runs</th>
                  <th style="padding:.45rem;">Balls</th>
                  <th style="padding:.45rem;">SR</th>
                  <th style="padding:.45rem;">Wkts</th>
                  <th style="padding:.45rem;">Overs</th>
                  <th style="padding:.45rem;">Eco</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let stat of player?.recent_stats" style="border-bottom:1px solid var(--border);">
                  <td style="padding:.45rem;">{{ stat.match_name }}</td>
                  <td style="padding:.45rem;">{{ stat.match_date }}</td>
                  <td style="padding:.45rem;">{{ stat.runs_scored ?? '-' }}</td>
                  <td style="padding:.45rem;">{{ stat.balls_faced ?? '-' }}</td>
                  <td style="padding:.45rem;">{{ stat.strike_rate ?? '-' }}</td>
                  <td style="padding:.45rem;">{{ stat.wickets_taken ?? '-' }}</td>
                  <td style="padding:.45rem;">{{ stat.overs_bowled ?? '-' }}</td>
                  <td style="padding:.45rem;">{{ stat.economy ?? '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class PlayerDetailComponent implements OnInit, OnDestroy {
  player: Player | null = null;
  analytics: PlayerAnalytics | null = null;
  loading = false;
  lastUpdatedAt = '';
  private playerId = 0;
  private autoRefreshTimer: any;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    this.playerId = Number(this.route.snapshot.paramMap.get('id') || 0);
    if (!this.playerId) return;

    this.loadPlayerData();

    // Auto-refresh every 45 seconds
    this.autoRefreshTimer = setInterval(() => {
      this.loadPlayerData();
    }, 45000);
  }

  ngOnDestroy(): void {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer);
    }
  }

  private loadPlayerData(): void {
    this.api.getPlayer(this.playerId).subscribe({
      next: (response) => {
        this.player = response;
        this.updateTimestamp();
      },
    });

    this.api.getPlayerAnalytics(this.playerId).subscribe({
      next: (response) => {
        this.analytics = response;
        this.updateTimestamp();
      },
      error: () => {
        this.analytics = null;
      },
    });
  }

  public refreshNow(): void {
    this.loading = true;
    this.loadPlayerData();
    setTimeout(() => {
      this.loading = false;
    }, 500);
  }

  private updateTimestamp(): void {
    const now = new Date();
    this.lastUpdatedAt = now.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }
}
