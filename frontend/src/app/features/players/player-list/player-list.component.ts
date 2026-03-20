import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Player } from '../../../core/services/api.service';

@Component({
  selector: 'app-player-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Players</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Search players and open profile analytics.</p>

        <div style="display:flex; gap:.5rem; margin-top:.75rem;">
          <input class="input" [(ngModel)]="query" placeholder="Search by name, country, team" />
          <button class="btn btn-primary" (click)="load()">Search</button>
        </div>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading players...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>
          <div *ngFor="let player of players" class="list-row">
            <a [routerLink]="['/players', player.id]"><strong>{{ player.name }}</strong></a>
            <div class="text-secondary">{{ player.country }} · {{ player.role }}</div>
          </div>
          <p *ngIf="!loading && !error && players.length === 0" class="text-secondary">No players found.</p>
        </div>
      </div>
    </div>
  `,
})
export class PlayerListComponent implements OnInit {
  query = '';
  players: Player[] = [];
  loading = false;
  error = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';
    const filters = this.query ? { search: this.query } : undefined;
    this.api.getPlayers(filters).subscribe({
      next: (response) => {
        this.players = response.results;
        this.loading = false;
      },
      error: () => {
        this.players = [];
        this.loading = false;
        this.error = 'Unable to load players right now.';
      },
    });
  }
}
