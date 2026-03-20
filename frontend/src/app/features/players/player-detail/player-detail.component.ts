import { Component, OnInit } from '@angular/core';
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
        <h1>Player</h1>
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
          <p class="text-secondary" *ngIf="analytics.avg_runs !== undefined">Avg Runs: {{ analytics.avg_runs }}</p>
          <p class="text-secondary" *ngIf="analytics.avg_wickets !== undefined">Avg Wickets: {{ analytics.avg_wickets }}</p>
        </div>
      </div>
    </div>
  `,
})
export class PlayerDetailComponent implements OnInit {
  player: Player | null = null;
  analytics: PlayerAnalytics | null = null;

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id') || 0);
    if (!id) return;

    this.api.getPlayer(id).subscribe({
      next: (response) => {
        this.player = response;
      },
    });

    this.api.getPlayerAnalytics(id).subscribe({
      next: (response) => {
        this.analytics = response;
      },
      error: () => {
        this.analytics = null;
      },
    });
  }
}
