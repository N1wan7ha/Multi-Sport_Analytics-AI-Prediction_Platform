import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, Match } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';

type MatchFormatFilter = 'all' | 't20' | 'odi' | 'test';
type MatchCategoryFilter = 'all' | 'international' | 'franchise' | 'domestic';

@Component({
  selector: 'app-favorites-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <section class="card" style="margin-bottom:1rem;">
        <h1>Favorites</h1>
        <p class="text-secondary" style="margin-top:.45rem;">
          Your saved teams and players with quick filters for format and match type.
        </p>

        <div style="margin-top:.75rem; display:flex; gap:.5rem; flex-wrap:wrap;">
          <button class="btn btn-primary" (click)="toggleEditMode()">{{ editMode ? 'Close Editor' : 'Add / Edit Favorites' }}</button>
          <button class="btn btn-secondary" (click)="loadRecommendedMatches()">Refresh Recommendations</button>
        </div>
      </section>

      <section class="card" style="margin-bottom:1rem;" *ngIf="editMode">
        <h3>Edit Favourite Teams and Players</h3>
        <p class="text-secondary" style="margin-top:.35rem;">Use checkboxes and click update to save your selection.</p>

        <div style="display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); margin-top:.75rem;">
          <div>
            <h4 style="margin:0 0 .45rem;">Teams</h4>
            <div style="display:grid; gap:.45rem; max-height:260px; overflow:auto; padding-right:.2rem;">
              <label *ngFor="let team of teamOptions" style="display:flex; gap:.45rem; align-items:center;">
                <input type="checkbox" [checked]="selectedTeamIds.has(team.id)" (change)="toggleTeam(team.id, $event)" />
                <span>{{ team.name }}</span>
              </label>
            </div>
          </div>

          <div>
            <h4 style="margin:0 0 .45rem;">Players</h4>
            <input class="input" [(ngModel)]="playerQuery" (ngModelChange)="onPlayerQueryChange()" placeholder="Search players" style="margin-bottom:.55rem;" />
            <div style="display:grid; gap:.45rem; max-height:260px; overflow:auto; padding-right:.2rem;">
              <label *ngFor="let player of playerOptions" style="display:flex; gap:.45rem; align-items:center;">
                <input type="checkbox" [checked]="selectedPlayerIds.has(player.id)" (change)="togglePlayer(player.id, $event)" />
                <span>{{ player.name }} <span class="text-secondary" *ngIf="player.team_name">· {{ player.team_name }}</span></span>
              </label>
            </div>
          </div>
        </div>

        <p *ngIf="editError" class="status-error" style="margin-top:.7rem;">{{ editError }}</p>

        <div style="margin-top:.85rem; display:flex; gap:.5rem; flex-wrap:wrap;">
          <button class="btn btn-primary" (click)="saveFavorites()" [disabled]="saving">{{ saving ? 'Updating...' : 'Update Favorites' }}</button>
          <button class="btn btn-secondary" (click)="resetEditorSelection()">Reset Selection</button>
        </div>
      </section>

      <section class="card" style="margin-bottom:1rem;">
        <h3>Quick Filters</h3>
        <div style="margin-top:.7rem; display:flex; flex-wrap:wrap; gap:.5rem;">
          <button
            *ngFor="let option of formatOptions"
            class="chip-btn"
            [class.chip-active]="formatFilter === option"
            (click)="setFormat(option)"
          >
            {{ option === 'all' ? 'All Formats' : (option | uppercase) }}
          </button>
        </div>
        <div style="margin-top:.55rem; display:flex; flex-wrap:wrap; gap:.5rem;">
          <button
            *ngFor="let option of categoryOptions"
            class="chip-btn"
            [class.chip-active]="categoryFilter === option"
            (click)="setCategory(option)"
          >
            {{ option === 'all' ? 'All Types' : option }}
          </button>
        </div>
      </section>

      <div style="display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));">
        <section class="card">
          <h3>Favourite Teams</h3>
          <p *ngIf="favouriteTeams.length === 0" class="text-secondary">No teams selected yet.</p>
          <div *ngFor="let team of favouriteTeams" class="list-row">
            <strong>{{ team.name }}</strong>
            <span class="text-secondary">{{ team.short_name || 'Team' }}</span>
          </div>
        </section>

        <section class="card">
          <h3>Favourite Players</h3>
          <p *ngIf="favouritePlayers.length === 0" class="text-secondary">No players selected yet.</p>
          <div *ngFor="let player of favouritePlayers" class="list-row">
            <strong>{{ player.name }}</strong>
            <span class="text-secondary">{{ player.team_name || player.country || 'Player' }}</span>
          </div>
        </section>
      </div>

      <section class="card" style="margin-top:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap;">
          <h3 style="margin:0;">Recommended Matches from Favorites</h3>
          <button class="btn btn-secondary" (click)="toggleEditMode()">Edit Teams/Players</button>
        </div>

        <p *ngIf="loadingMatches" class="text-secondary" style="margin-top:.7rem;">Loading matches...</p>
        <p *ngIf="!loadingMatches && recommendedMatches.length === 0" class="text-secondary" style="margin-top:.7rem;">
          No matching fixtures for your current filters.
        </p>

        <div *ngFor="let match of recommendedMatches" class="list-row" style="display:grid; gap:.3rem;">
          <div><strong>{{ match.team1?.name || 'Unknown' }}</strong> vs <strong>{{ match.team2?.name || 'Unknown' }}</strong></div>
          <div class="text-secondary">{{ match.format | uppercase }} · {{ match.category }} · {{ match.status }}</div>
          <div style="display:flex; gap:.45rem; flex-wrap:wrap;">
            <a [routerLink]="['/matches', match.id]" class="btn btn-secondary">Open Match</a>
            <a [routerLink]="['/matches', match.id, 'predict']" class="btn btn-primary">Predict</a>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .chip-btn {
      border: 1px solid var(--border-muted);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.02);
      color: var(--text-secondary);
      padding: 0.28rem 0.7rem;
      cursor: pointer;
      text-transform: capitalize;
      font-size: 0.76rem;
    }

    .chip-btn.chip-active {
      border-color: var(--border-primary);
      color: var(--text-primary);
      background: rgba(0, 212, 170, 0.16);
    }
  `],
})
export class FavoritesOverviewComponent implements OnInit {
  favouriteTeams: Array<{ id: number; name: string; short_name?: string }> = [];
  favouritePlayers: Array<{ id: number; name: string; team_name?: string; country?: string }> = [];
  recommendedMatches: Match[] = [];
  teamOptions: Array<{ id: number; name: string; short_name?: string }> = [];
  playerOptions: Array<{ id: number; name: string; team_name?: string; country?: string }> = [];
  selectedTeamIds = new Set<number>();
  selectedPlayerIds = new Set<number>();
  editMode = false;
  playerQuery = '';
  saving = false;
  editError = '';
  private playerSearchTimer: ReturnType<typeof setTimeout> | null = null;
  loadingMatches = false;
  formatFilter: MatchFormatFilter = 'all';
  categoryFilter: MatchCategoryFilter = 'all';
  readonly formatOptions: MatchFormatFilter[] = ['all', 't20', 'odi', 'test'];
  readonly categoryOptions: MatchCategoryFilter[] = ['all', 'international', 'franchise', 'domestic'];

  constructor(private auth: AuthService, private api: ApiService) {}

  ngOnInit(): void {
    this.auth.loadProfile().subscribe({
      next: (profile) => {
        this.favouriteTeams = (profile.favourite_teams || []).map((team) => ({
          id: team.id,
          name: team.name,
          short_name: team.short_name,
        }));
        this.favouritePlayers = (profile.favourite_players || []).map((player) => ({
          id: player.id,
          name: player.name,
          team_name: player.team_name,
          country: player.country,
        }));
        this.selectedTeamIds = new Set(this.favouriteTeams.map((team) => team.id));
        this.selectedPlayerIds = new Set(this.favouritePlayers.map((player) => player.id));
        this.loadTeamOptions();
        this.loadPlayerOptions();
        this.loadRecommendedMatches();
      },
      error: () => {
        this.favouriteTeams = [];
        this.favouritePlayers = [];
        this.selectedTeamIds = new Set();
        this.selectedPlayerIds = new Set();
        this.loadTeamOptions();
        this.loadPlayerOptions();
        this.loadRecommendedMatches();
      },
    });
  }

  setFormat(value: MatchFormatFilter): void {
    this.formatFilter = value;
    this.loadRecommendedMatches();
  }

  setCategory(value: MatchCategoryFilter): void {
    this.categoryFilter = value;
    this.loadRecommendedMatches();
  }

  loadRecommendedMatches(): void {
    this.loadingMatches = true;
    const favouriteTeamIds = this.favouriteTeams.map((team) => team.id);
    this.api.getMatches({
      status: 'upcoming',
      format: this.formatFilter !== 'all' ? this.formatFilter : undefined,
      category: this.categoryFilter !== 'all' ? this.categoryFilter : undefined,
      recommendation: true,
      favoriteTeamIds: favouriteTeamIds,
    }).subscribe({
      next: (response) => {
        this.recommendedMatches = response.results.slice(0, 12);
        this.loadingMatches = false;
      },
      error: () => {
        this.recommendedMatches = [];
        this.loadingMatches = false;
      },
    });
  }

  toggleEditMode(): void {
    this.editMode = !this.editMode;
    this.editError = '';
  }

  onPlayerQueryChange(): void {
    if (this.playerSearchTimer) {
      clearTimeout(this.playerSearchTimer);
    }
    this.playerSearchTimer = setTimeout(() => {
      this.loadPlayerOptions(this.playerQuery);
    }, 260);
  }

  toggleTeam(teamId: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.selectedTeamIds.add(teamId);
    } else {
      this.selectedTeamIds.delete(teamId);
    }
  }

  togglePlayer(playerId: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.selectedPlayerIds.add(playerId);
    } else {
      this.selectedPlayerIds.delete(playerId);
    }
  }

  resetEditorSelection(): void {
    this.selectedTeamIds = new Set(this.favouriteTeams.map((team) => team.id));
    this.selectedPlayerIds = new Set(this.favouritePlayers.map((player) => player.id));
    this.editError = '';
  }

  saveFavorites(): void {
    this.saving = true;
    this.editError = '';
    this.auth.updateProfile({
      favourite_team_ids: Array.from(this.selectedTeamIds.values()),
      favourite_player_ids: Array.from(this.selectedPlayerIds.values()),
    }).subscribe({
      next: (profile) => {
        this.saving = false;
        this.favouriteTeams = (profile.favourite_teams || []).map((team) => ({
          id: team.id,
          name: team.name,
          short_name: team.short_name,
        }));
        this.favouritePlayers = (profile.favourite_players || []).map((player) => ({
          id: player.id,
          name: player.name,
          team_name: player.team_name,
          country: player.country,
        }));
        this.selectedTeamIds = new Set(this.favouriteTeams.map((team) => team.id));
        this.selectedPlayerIds = new Set(this.favouritePlayers.map((player) => player.id));
        this.loadRecommendedMatches();
      },
      error: (err) => {
        this.saving = false;
        this.editError = err?.error?.detail || 'Unable to update favorites right now.';
      },
    });
  }

  private loadTeamOptions(): void {
    this.auth.getTeamOptions().subscribe({
      next: (teams) => {
        this.teamOptions = teams;
      },
      error: () => {
        this.teamOptions = [];
      },
    });
  }

  private loadPlayerOptions(query = ''): void {
    this.auth.getPlayerOptions(query).subscribe({
      next: (players) => {
        this.playerOptions = players.slice(0, 220).map((player) => ({
          id: player.id,
          name: player.name,
          team_name: player.team_name,
          country: player.country,
        }));
      },
      error: () => {
        this.playerOptions = [];
      },
    });
  }
}
