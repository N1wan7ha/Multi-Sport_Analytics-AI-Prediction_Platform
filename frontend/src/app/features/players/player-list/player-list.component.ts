import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Player, PlayerAnalytics, TopPlayer } from '../../../core/services/api.service';

interface FilterOption {
  label: string;
  value: string;
  count: number;
}

@Component({
  selector: 'app-player-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Players</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Trending players by default, then search and drill into full player data.</p>

        <div class="hero-strip" *ngIf="trendingPlayers.length > 0">
          <div class="hero-chip">
            <span>Trending Players</span>
            <strong>{{ trendingPlayers.length }}</strong>
          </div>
          <div class="hero-chip">
            <span>Total Catalog</span>
            <strong>{{ players.length }}</strong>
          </div>
          <div class="hero-chip">
            <span>Visible</span>
            <strong>{{ filteredPlayers().length }}</strong>
          </div>
        </div>

        <div style="display:flex; gap:.5rem; margin-top:.75rem; flex-wrap:wrap;">
          <input class="input" [(ngModel)]="query" (ngModelChange)="applyFilters()" placeholder="Search by player, country, team" />
          <button class="btn btn-primary" (click)="load()">Refresh</button>
          <button class="btn btn-secondary" (click)="loadTrendingPlayers()">Refresh Trending</button>
          <span class="text-secondary" style="align-self:center; font-size:.84rem;">Showing {{ filteredPlayers().length }} of {{ players.length }}</span>
        </div>

        <div style="margin-top:.9rem;" *ngIf="trendingPlayers.length > 0">
          <h3 style="margin:0 0 .55rem 0;">Trending Right Now</h3>
          <div class="trend-grid">
            <button class="trend-card" *ngFor="let player of trendingPlayers.slice(0, 8)" (click)="selectTrendingPlayer(player)">
              <strong>{{ player.name }}</strong>
              <p class="text-secondary" style="font-size:.78rem; margin-top:.2rem;">{{ player.country || 'Unknown' }}</p>
              <p class="text-secondary" style="font-size:.78rem; margin-top:.2rem;" *ngIf="player.matches">{{ player.matches }} matches</p>
            </button>
          </div>
        </div>

        <div style="margin-top:.75rem; display:flex; gap:.5rem; flex-wrap:wrap; align-items:center;">
          <label *ngIf="countryOptions().length > 0">
            <span class="text-secondary" style="font-size:.8rem; display:block; margin-bottom:.25rem;">Country</span>
            <select class="input" [(ngModel)]="selectedCountry" (ngModelChange)="applyFilters()" style="min-width:220px;">
              <option value="all">All Countries</option>
              <option *ngFor="let country of countryOptions()" [value]="country.value">{{ country.label }} ({{ country.count }})</option>
            </select>
          </label>
          <span *ngIf="countryOptions().length === 0" class="text-secondary" style="font-size:.84rem;">Country data is not available for current results.</span>

          <label *ngIf="roleOptions().length > 0">
            <span class="text-secondary" style="font-size:.8rem; display:block; margin-bottom:.25rem;">Role</span>
            <select class="input" [(ngModel)]="selectedRole" (ngModelChange)="applyFilters()" style="min-width:220px;">
              <option value="all">All Roles</option>
              <option *ngFor="let role of roleOptions()" [value]="role.value">{{ role.label }} ({{ role.count }})</option>
            </select>
          </label>
          <span *ngIf="roleOptions().length === 0" class="text-secondary" style="font-size:.84rem;">Role data is not available for current results.</span>

          <button class="btn btn-secondary" (click)="resetCategoryFilters()">Reset Filters</button>
        </div>

        <div class="spotlight" *ngIf="selectedPlayer">
          <div style="display:flex; justify-content:space-between; gap:.6rem; flex-wrap:wrap; align-items:center;">
            <div>
              <h3 style="margin:0;">Player Spotlight</h3>
              <p class="text-secondary" style="font-size:.84rem; margin-top:.2rem;">{{ selectedPlayer.name }} · {{ displayCountry(selectedPlayer) }}</p>
            </div>
            <div style="display:flex; gap:.4rem; flex-wrap:wrap;">
              <a class="btn btn-secondary" [routerLink]="['/players', selectedPlayer.id]">Full Profile</a>
              <button class="btn btn-secondary" (click)="clearSelection()" [disabled]="trendingPlayers.length === 0">Replace</button>
            </div>
          </div>

          <div class="spotlight-grid" *ngIf="selectedPlayerAnalytics">
            <div class="spotlight-chip">
              <span>Matches</span>
              <strong>{{ selectedPlayerAnalytics.matches_played || 0 }}</strong>
            </div>
            <div class="spotlight-chip">
              <span>Total Runs</span>
              <strong>{{ selectedPlayerAnalytics.total_runs || 0 }}</strong>
            </div>
            <div class="spotlight-chip">
              <span>Total Wickets</span>
              <strong>{{ selectedPlayerAnalytics.total_wickets || 0 }}</strong>
            </div>
            <div class="spotlight-chip">
              <span>Strike Rate</span>
              <strong>{{ (selectedPlayerAnalytics.average_strike_rate || 0) | number:'1.1-2' }}</strong>
            </div>
          </div>

          <div style="margin-top:.65rem; padding:.75rem; background:rgba(94,234,212,0.08); border-radius:8px; border:1px solid rgba(94,234,212,0.2);" *ngIf="!selectedPlayerAnalytics">
            <p class="text-secondary" style="margin:0; font-size:.84rem;">Statistics not available yet. Visit the full profile for detailed career data.</p>
          </div>
        </div>

        <div style="margin-top:.75rem; padding:1rem; background:rgba(249,115,22,0.08); border-radius:8px; border:1px solid rgba(249,115,22,0.2);" *ngIf="!selectedPlayer">
          <p class="text-secondary" style="margin:0; font-size:.84rem;">No player selected. Click "Select" next to a player below or choose from trending players above.</p>
        </div>

        <div style="margin-top:1rem;">
          <p *ngIf="loading" class="text-secondary">Loading players...</p>
          <p *ngIf="error" class="status-error">{{ error }}</p>
          <div *ngFor="let player of filteredPlayers()" class="list-row">
            <div style="display:flex; justify-content:space-between; gap:.6rem; align-items:center; flex-wrap:wrap;">
              <div>
                <a [routerLink]="['/players', player.id]"><strong>{{ player.name }}</strong></a>
                <div class="text-secondary">{{ displayCountry(player) }} · {{ displayRole(player) }}</div>
              </div>
              <button class="btn btn-secondary" (click)="selectPlayer(player)">Select</button>
            </div>
          </div>
          <p *ngIf="!loading && !error && filteredPlayers().length === 0" class="text-secondary">No players found for current filters.</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .hero-strip {
      margin-top: 0.75rem;
      display: grid;
      gap: 0.5rem;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    }

    .hero-chip {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
      padding: 0.55rem 0.65rem;
    }

    .hero-chip span {
      font-size: 0.7rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      display: block;
    }

    .hero-chip strong {
      font-size: 1.1rem;
      color: #67e8f9;
    }

    .trend-grid {
      display: grid;
      gap: 0.55rem;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    }

    .trend-card {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
      text-align: left;
      padding: 0.62rem;
      cursor: pointer;
      color: var(--text-primary);
      transition: border-color var(--transition-fast), transform var(--transition-fast);
    }

    .trend-card:hover {
      border-color: rgba(103, 232, 249, 0.35);
      transform: translateY(-1px);
    }

    .spotlight {
      margin-top: 0.95rem;
      border: 1px solid rgba(103, 232, 249, 0.24);
      border-radius: var(--radius-lg);
      background: linear-gradient(150deg, rgba(10, 17, 31, 0.95), rgba(12, 24, 42, 0.94));
      padding: 0.85rem;
    }

    .spotlight-grid {
      margin-top: 0.75rem;
      display: grid;
      gap: 0.5rem;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    }

    .spotlight-chip {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 0.5rem;
      background: rgba(255, 255, 255, 0.02);
      display: grid;
      gap: 0.1rem;
    }

    .spotlight-chip span {
      font-size: 0.7rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .spotlight-chip strong {
      font-size: 1rem;
      color: #5eead4;
    }
  `],
})
export class PlayerListComponent implements OnInit {
  query = '';
  players: Player[] = [];
  filteredRows: Player[] = [];
  trendingPlayers: TopPlayer[] = [];
  selectedPlayer: Player | null = null;
  selectedPlayerAnalytics: PlayerAnalytics | null = null;
  selectedCountry = 'all';
  selectedRole = 'all';
  loading = false;
  error = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadTrendingPlayers();
    this.load();
  }

  loadTrendingPlayers(): void {
    this.api.getTopPlayers('matches', 20).subscribe({
      next: (response) => {
        this.trendingPlayers = response.results || [];
        if (!this.selectedPlayer && this.trendingPlayers.length > 0) {
          this.selectTrendingPlayer(this.trendingPlayers[0]);
        }
      },
      error: () => {
        this.trendingPlayers = [];
      },
    });
  }

  selectTrendingPlayer(player: TopPlayer): void {
    const existing = this.players.find((row) => row.id === player.id);
    if (existing) {
      this.selectedPlayer = existing;
    } else {
      this.api.getPlayer(player.id).subscribe({
        next: (response) => {
          this.selectedPlayer = response;
        },
        error: () => {
          this.selectedPlayer = {
            id: player.id,
            name: player.name,
            full_name: player.name,
            country: player.country,
            role: player.role,
          } as Player;
        },
      });
    }

    this.api.getPlayerAnalytics(player.id).subscribe({
      next: (analytics) => {
        this.selectedPlayerAnalytics = analytics;
      },
      error: () => {
        this.selectedPlayerAnalytics = null;
      },
    });
  }

  selectPlayer(player: Player): void {
    this.selectedPlayer = player;
    this.api.getPlayerAnalytics(player.id).subscribe({
      next: (analytics) => {
        this.selectedPlayerAnalytics = analytics;
      },
      error: () => {
        this.selectedPlayerAnalytics = null;
      },
    });
  }

  clearSelection(): void {
    this.selectedPlayer = null;
    this.selectedPlayerAnalytics = null;
    if (this.trendingPlayers.length > 0) {
      this.selectTrendingPlayer(this.trendingPlayers[0]);
    }
  }

  load(): void {
    this.loading = true;
    this.error = '';
    const filters = this.query ? { search: this.query } : undefined;
    this.api.getPlayers(filters).subscribe({
      next: (response) => {
        this.players = response.results;
        this.applyFilters();
        this.loading = false;
      },
      error: () => {
        this.players = [];
        this.filteredRows = [];
        this.loading = false;
        this.error = 'Unable to load players right now.';
      },
    });
  }

  countryOptions(): FilterOption[] {
    return this.buildOptions(this.players.map((player) => this.normalizeCountry(player)));
  }

  roleOptions(): FilterOption[] {
    return this.buildOptions(this.players.map((player) => this.normalizeRole(player)));
  }

  filteredPlayers(): Player[] {
    return this.filteredRows;
  }

  resetCategoryFilters(): void {
    this.query = '';
    this.selectedCountry = 'all';
    this.selectedRole = 'all';
    this.applyFilters();
  }

  displayCountry(player: Player): string {
    const value = this.normalizeCountry(player);
    return value === 'unknown' ? 'Country not available' : value;
  }

  displayRole(player: Player): string {
    const value = this.normalizeRole(player);
    return value === 'unknown' ? 'Role not available' : value;
  }

  applyFilters(): void {
    const q = this.query.trim().toLowerCase();
    this.filteredRows = this.players
      .filter((player) => {
        const country = this.normalizeCountry(player);
        const role = this.normalizeRole(player);

        const countryOk = this.selectedCountry === 'all' || country === this.selectedCountry;
        const roleOk = this.selectedRole === 'all' || role === this.selectedRole;

        const searchable = [
          player.name || '',
          player.full_name || '',
          country,
          role,
          player.team?.name || '',
        ].join(' ').toLowerCase();

        const queryOk = !q || searchable.includes(q);
        return countryOk && roleOk && queryOk;
      })
      .sort((a, b) => (a.name || '').localeCompare(b.name || ''));

    if (!this.query.trim() && this.selectedCountry === 'all' && this.selectedRole === 'all' && this.trendingPlayers.length > 0) {
      const trendingOrder = new Map<number, number>();
      this.trendingPlayers.forEach((item, index) => trendingOrder.set(item.id, index));
      this.filteredRows = this.filteredRows.sort((a, b) => {
        const ai = trendingOrder.has(a.id) ? trendingOrder.get(a.id)! : Number.MAX_SAFE_INTEGER;
        const bi = trendingOrder.has(b.id) ? trendingOrder.get(b.id)! : Number.MAX_SAFE_INTEGER;
        if (ai === bi) {
          return (a.name || '').localeCompare(b.name || '');
        }
        return ai - bi;
      });
    }
  }

  private normalizeCountry(player: Player): string {
    const value = (player.country || '').trim();
    return value ? value : 'unknown';
  }

  private normalizeRole(player: Player): string {
    const value = (player.role || '').trim();
    return value ? value : 'unknown';
  }

  private buildOptions(values: string[]): FilterOption[] {
    const counts = new Map<string, number>();
    for (const value of values) {
      if (!value || value === 'unknown') {
        continue;
      }
      counts.set(value, (counts.get(value) || 0) + 1);
    }

    return Array.from(counts.entries())
      .map(([value, count]) => ({ label: value, value, count }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }
}
