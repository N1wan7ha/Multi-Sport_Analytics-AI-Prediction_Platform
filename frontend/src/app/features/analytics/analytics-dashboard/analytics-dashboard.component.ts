import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, PlayerAnalytics, PlayerOption, TeamAnalytics, TeamOption, InternationalTeam, TopPlayer, InternationalStanding } from '../../../core/services/api.service';

type MatchFormatFilter = 'all' | 't20' | 'odi' | 'test';
type MatchCategoryFilter = 'all' | 'international' | 'franchise' | 'domestic';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up analytics-page">
      <div class="card analytics-hero" style="margin-bottom:1rem;">
        <h1>Analytics</h1>
        <p class="text-secondary" style="margin-top:0.5rem">International standings, team intelligence, and player form in one command center.</p>

        <div class="hero-strip">
          <div class="hero-chip">
            <span>Standings</span>
            <strong>{{ internationalStandings.length }}</strong>
          </div>
          <div class="hero-chip">
            <span>International Teams</span>
            <strong>{{ internationalTeams.length }}</strong>
          </div>
          <div class="hero-chip">
            <span>Top Players</span>
            <strong>{{ topPlayers.length }}</strong>
          </div>
        </div>

        <div style="display:flex; gap:.55rem; align-items:center; flex-wrap:wrap; margin-top:.6rem;">
          <button class="btn btn-secondary" (click)="loadInternationalData()">Refresh Live Data</button>
          <p class="text-secondary" style="font-size:.78rem; margin:0;" *ngIf="lastUpdatedAt">
            Last updated: {{ lastUpdatedAt | date:'mediumTime' }}
          </p>
        </div>

        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.8rem;">
          <button
            *ngFor="let option of formatOptions"
            class="chip-btn"
            [class.chip-active]="formatFilter === option"
            (click)="setFormatFilter(option)"
          >
            {{ option === 'all' ? 'All Formats' : (option | uppercase) }}
          </button>
        </div>
        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.55rem;">
          <button
            *ngFor="let option of categoryOptions"
            class="chip-btn"
            [class.chip-active]="categoryFilter === option"
            (click)="setCategoryFilter(option)"
          >
            {{ option === 'all' ? 'All Types' : option }}
          </button>
        </div>

        <div style="margin-top:.8rem; display:grid; gap:.5rem; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));" *ngIf="teamOptions.length > 0 || playerOptions.length > 0">
          <button class="list-row" style="cursor:pointer; background:transparent; text-align:left;" *ngFor="let team of suggestedTeams()" (click)="selectSuggestedTeam(team.name)">
            <strong>Suggested Team</strong>
            <span class="text-secondary">{{ team.name }}</span>
          </button>
          <button class="list-row" style="cursor:pointer; background:transparent; text-align:left;" *ngFor="let player of suggestedPlayers()" (click)="selectSuggestedPlayer(player.id)">
            <strong>Suggested Player</strong>
            <span class="text-secondary">{{ player.name }}{{ player.team_name ? ' · ' + player.team_name : '' }}</span>
          </button>
        </div>
      </div>

      <div class="grid" style="display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(290px,1fr));">
        <div class="card analytics-panel">
          <h3>Team Analytics</h3>
          <p class="text-secondary" style="margin-top:.35rem;">Pick a team and get instant trend stats.</p>

          <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.75rem;">
            <select class="input" [(ngModel)]="selectedTeamName">
              <option value="">Choose a team...</option>
              <option *ngFor="let team of filteredTeamOptions()" [value]="team.name">{{ team.name }}</option>
            </select>
            <button class="btn btn-primary" (click)="loadTeamAnalytics()" [disabled]="teamLoading || !selectedTeamName">
              {{ teamLoading ? 'Loading...' : 'Load Team' }}
            </button>
          </div>

          <p *ngIf="teamError" class="status-error" style="margin-top:.75rem;">{{ teamError }}</p>

          <div *ngIf="teamAnalytics" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem; display:grid; gap:.35rem;">
            <p><strong>{{ teamAnalytics.team }}</strong></p>
            <p><strong>Win Rate:</strong> {{ teamAnalytics.win_rate_percent }}%</p>
            <p><strong>Wins:</strong> {{ teamAnalytics.wins }} · <strong>Losses:</strong> {{ teamAnalytics.losses }}</p>
            <p><strong>Total:</strong> {{ teamAnalytics.total_matches }} · <strong>Completed:</strong> {{ teamAnalytics.completed_matches }}</p>
            <p *ngIf="teamAnalytics.recent_form?.length" class="text-secondary">
              Recent Form: {{ getRecentFormText(teamAnalytics.recent_form || []) }}
            </p>

            <div *ngIf="teamAnalytics.by_format as byFormat" style="margin-top:.45rem; display:grid; gap:.35rem;">
              <p class="text-secondary" style="font-size:.8rem;">Format Match Counts</p>
              <div class="list-row" *ngFor="let key of formatBreakdownKeys(byFormat)">
                <span>{{ key | uppercase }}</span>
                <strong>{{ byFormat[key] }}</strong>
              </div>
            </div>
          </div>
        </div>

        <div class="card analytics-panel">
          <h3>Player Analytics</h3>
          <p class="text-secondary" style="margin-top:.35rem;">Search player name and load stats in one click.</p>

          <div style="margin-top:.75rem; display:grid; gap:.45rem;">
            <input
              class="input"
              [(ngModel)]="playerSearch"
              (ngModelChange)="onPlayerSearchChange()"
              placeholder="Search player by name, team or country"
            />
            <select class="input" [(ngModel)]="selectedPlayerId">
              <option [ngValue]="0">Choose a player...</option>
              <option *ngFor="let player of playerOptions" [ngValue]="player.id">
                {{ player.name }}{{ player.team_name ? ' · ' + player.team_name : '' }}
              </option>
            </select>

            <button class="btn btn-secondary" (click)="loadPlayerAnalytics()" [disabled]="playerLoading || !selectedPlayerId">
              {{ playerLoading ? 'Loading...' : 'Load Player' }}
            </button>
          </div>

          <p *ngIf="playerError" class="status-error" style="margin-top:.75rem;">{{ playerError }}</p>

          <div *ngIf="playerAnalytics" style="margin-top:1rem; border-top:1px solid var(--border); padding-top:1rem; display:grid; gap:.35rem;">
            <p><strong>{{ playerAnalytics.player_name }}</strong></p>
            <p><strong>Matches:</strong> {{ playerAnalytics.matches_played }}</p>
            <p><strong>Total Runs:</strong> {{ playerAnalytics.total_runs }}</p>
            <p><strong>Total Wickets:</strong> {{ playerAnalytics.total_wickets }}</p>
            <p><strong>Batting Avg:</strong> {{ playerAnalytics.batting_average || 0 }}</p>
            <p><strong>Strike Rate:</strong> {{ playerAnalytics.average_strike_rate || 0 }}</p>
            <p><strong>Economy:</strong> {{ playerAnalytics.average_economy || 0 }}</p>
          </div>
        </div>
      </div>

      <div class="card analytics-panel" style="margin-top:1rem;" *ngIf="teamAnalytics || playerAnalytics">
        <h3>Quick Summary</h3>
        <p class="text-secondary" style="margin-top:.45rem;">
          Focus: {{ formatFilter === 'all' ? 'All formats' : (formatFilter | uppercase) }} ·
          {{ categoryFilter === 'all' ? 'All match types' : categoryFilter }}
        </p>
        <p class="text-secondary" *ngIf="teamAnalytics" style="margin-top:.35rem;">
          Team {{ teamAnalytics.team }} has {{ teamAnalytics.win_rate_percent }}% win rate from {{ teamAnalytics.completed_matches }} completed games.
        </p>
        <p class="text-secondary" *ngIf="playerAnalytics" style="margin-top:.35rem;">
          Player {{ playerAnalytics.player_name }} has {{ playerAnalytics.total_runs }} runs and {{ playerAnalytics.total_wickets }} wickets.
        </p>
      </div>

      <div class="card analytics-panel" style="margin-top:1rem;">
        <h3>International Standings</h3>
        <p class="text-secondary" style="margin-top:.35rem;">Top-ranked international players by format.</p>

        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.75rem;">
          <button
            *ngFor="let fmt of standingsFormats"
            class="chip-btn"
            [class.chip-active]="standingsFormat === fmt"
            (click)="setStandingsFormat(fmt)"
          >
            {{ fmt | uppercase }}
          </button>
        </div>

        <div *ngIf="standingsLoading" class="text-secondary" style="margin-top:.75rem;">Loading standings...</div>
        <div *ngIf="!standingsLoading && internationalStandings.length > 0" style="margin-top:.75rem;">
          <div class="list-row" *ngFor="let standing of internationalStandings.slice(0, 10)">
            <div style="display:flex; gap:.5rem; align-items:center; flex:1;">
              <strong style="min-width:1.5rem;">{{ standing.rank }}</strong>
              <div style="flex:1;">
                <strong>{{ standing.player }}</strong>
                <p class="text-secondary" style="font-size:.75rem; margin:0;">{{ standing.country }}</p>
              </div>
            </div>
            <div style="text-align:right;">
              <strong>{{ standing.rating }}</strong>
              <p class="text-secondary" style="font-size:.75rem; margin:0;">{{ standing.matches }} matches</p>
            </div>
          </div>
        </div>
      </div>

      <div class="card analytics-panel" style="margin-top:1rem;">
        <h3>International Teams</h3>
        <p class="text-secondary" style="margin-top:.35rem;">Performance of international cricket teams.</p>

        <div *ngIf="internationalTeamsLoading" class="text-secondary" style="margin-top:.75rem;">Loading teams...</div>
        <div *ngIf="!internationalTeamsLoading && internationalTeams.length > 0" style="margin-top:.75rem;">
          <div class="list-row" *ngFor="let team of internationalTeams.slice(0, 8)">
            <div style="flex:1;">
              <strong>{{ team.name }}</strong>
              <p class="text-secondary" style="font-size:.75rem; margin:.15rem 0 0;">
                Win Rate: {{ team.win_rate }}% · {{ team.wins }}W-{{ team.losses }}L
              </p>
            </div>
            <div style="text-align:right;">
              <p class="text-secondary" style="font-size:.8rem; margin:0;">{{ team.total_matches }} matches</p>
              <p *ngIf="team.recent_form" class="text-secondary" style="font-size:.75rem; margin:.1rem 0 0; letter-spacing:.08em;">
                {{ team.recent_form }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="card analytics-panel" style="margin-top:1rem;">
        <h3>Top Players</h3>
        <p class="text-secondary" style="margin-top:.35rem;">Leading players across different metrics.</p>

        <div style="display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.75rem;">
          <button
            *ngFor="let metric of topPlayersMetrics"
            class="chip-btn"
            [class.chip-active]="topPlayersMetric === metric"
            (click)="setTopPlayersMetric(metric)"
          >
            {{ metric === 'matches' ? 'Most Matches' : (metric === 'runs' ? 'Most Runs' : 'Most Wickets') }}
          </button>
        </div>

        <div *ngIf="topPlayersLoading" class="text-secondary" style="margin-top:.75rem;">Loading players...</div>
        <div *ngIf="!topPlayersLoading && topPlayers.length > 0" style="margin-top:.75rem;">
          <div class="list-row" *ngFor="let player of topPlayers.slice(0, 8)">
            <div style="flex:1;">
              <strong>{{ player.name }}</strong>
              <p class="text-secondary" style="font-size:.75rem; margin:.15rem 0 0;">
                {{ player.country }}{{ player.team ? ' · ' + player.team.name : '' }} · {{ player.role }}
              </p>
            </div>
            <div style="text-align:right;">
              <strong *ngIf="topPlayersMetric === 'runs'">{{ player.total_runs || 0 }}</strong>
              <strong *ngIf="topPlayersMetric === 'wickets'">{{ player.total_wickets || 0 }}</strong>
              <strong *ngIf="topPlayersMetric === 'matches'">{{ player.matches }}</strong>
              <p class="text-secondary" style="font-size:.75rem; margin:.1rem 0 0;">
                {{ topPlayersMetric === 'runs' ? 'runs' : (topPlayersMetric === 'wickets' ? 'wickets' : 'matches') }}
              </p>
            </div>
          </div>
        </div>
        <p *ngIf="!topPlayersLoading && topPlayers.length === 0" class="text-secondary" style="margin-top:.75rem;">No top player records available right now.</p>
      </div>
    </div>
  `,
  styles: [`
    .analytics-page {
      background:
        radial-gradient(circle at 8% 8%, rgba(34, 211, 238, 0.08), transparent 26%),
        radial-gradient(circle at 92% 90%, rgba(16, 185, 129, 0.08), transparent 28%);
    }

    .analytics-hero {
      border: 1px solid rgba(56, 189, 248, 0.24);
      background:
        radial-gradient(circle at 92% 12%, rgba(6, 182, 212, 0.18), transparent 40%),
        linear-gradient(150deg, rgba(9, 16, 29, 0.96), rgba(12, 24, 42, 0.96));
      box-shadow: 0 16px 32px rgba(0, 0, 0, 0.24);
    }

    .hero-strip {
      margin-top: 0.85rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.55rem;
    }

    .hero-chip {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
      padding: 0.6rem 0.65rem;
      display: grid;
      gap: 0.12rem;
    }

    .hero-chip span {
      font-size: 0.69rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
    }

    .hero-chip strong {
      font-size: 1.25rem;
      color: #67e8f9;
      line-height: 1;
    }

    .analytics-panel {
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: linear-gradient(170deg, rgba(14, 23, 39, 0.9), rgba(11, 18, 33, 0.92));
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.18);
    }

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

    .list-row {
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
    }

    @media (max-width: 720px) {
      .hero-chip strong {
        font-size: 1.08rem;
      }
    }
  `],
})
export class AnalyticsDashboardComponent implements OnInit, OnDestroy {
  teamOptions: TeamOption[] = [];
  playerOptions: PlayerOption[] = [];
  selectedTeamName = '';
  selectedPlayerId = 0;
  playerSearch = '';
  formatFilter: MatchFormatFilter = 'all';
  categoryFilter: MatchCategoryFilter = 'all';
  readonly formatOptions: MatchFormatFilter[] = ['all', 't20', 'odi', 'test'];
  readonly categoryOptions: MatchCategoryFilter[] = ['all', 'international', 'franchise', 'domestic'];
  readonly standingsFormats: Array<'test' | 'odi' | 't20'> = ['test', 'odi', 't20'];
  readonly topPlayersMetrics: Array<'matches' | 'runs' | 'wickets'> = ['matches', 'runs', 'wickets'];
  teamAnalytics: TeamAnalytics | null = null;
  playerAnalytics: PlayerAnalytics | null = null;
  teamLoading = false;
  playerLoading = false;
  teamError = '';
  playerError = '';

  // International standings, teams, and top players
  internationalStandings: InternationalStanding[] = [];
  internationalTeams: InternationalTeam[] = [];
  topPlayers: TopPlayer[] = [];
  standingsFormat: 'test' | 'odi' | 't20' = 'test';
  topPlayersMetric: 'matches' | 'runs' | 'wickets' = 'matches';
  standingsLoading = false;
  internationalTeamsLoading = false;
  topPlayersLoading = false;
  lastUpdatedAt: Date | null = null;

  private autoRefreshTimer: ReturnType<typeof setInterval> | null = null;
  private playerSearchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private api: ApiService) {
    this.loadTeamOptions();
    this.loadPlayerOptions();
    this.loadInternationalData();
  }

  ngOnInit(): void {
    // Options are loaded in constructor; this keeps lifecycle explicit for future hooks.
    this.autoRefreshTimer = setInterval(() => {
      this.loadInternationalData();
      if (this.teamAnalytics && this.selectedTeamName) {
        this.loadTeamAnalytics();
      }
      if (this.playerAnalytics && this.selectedPlayerId) {
        this.loadPlayerAnalytics();
      }
    }, 45000);
  }

  ngOnDestroy(): void {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer);
      this.autoRefreshTimer = null;
    }
    if (this.playerSearchTimer) {
      clearTimeout(this.playerSearchTimer);
      this.playerSearchTimer = null;
    }
  }

  filteredTeamOptions(): TeamOption[] {
    return this.teamOptions.filter((team) => {
      if (this.categoryFilter === 'international') {
        return !!team.is_international;
      }
      if (this.categoryFilter === 'franchise' || this.categoryFilter === 'domestic') {
        return !team.is_international;
      }
      return true;
    });
  }

  setFormatFilter(value: MatchFormatFilter): void {
    this.formatFilter = value;
    this.refreshLoadedAnalytics();
  }

  setCategoryFilter(value: MatchCategoryFilter): void {
    this.categoryFilter = value;
    this.refreshLoadedAnalytics();
  }

  setStandingsFormat(fmt: 'test' | 'odi' | 't20'): void {
    this.standingsFormat = fmt;
    this.loadInternationalStandings();
  }

  setTopPlayersMetric(metric: 'matches' | 'runs' | 'wickets'): void {
    this.topPlayersMetric = metric;
    this.loadTopPlayers();
  }

  getRecentFormText(rows: Array<{ outcome: string }>): string {
    return rows.map((item) => item.outcome).join(' · ');
  }

  formatBreakdownKeys(byFormat: Record<string, number>): string[] {
    return Object.keys(byFormat).sort();
  }

  onPlayerSearchChange(): void {
    if (this.playerSearchTimer) {
      clearTimeout(this.playerSearchTimer);
    }

    this.playerSearchTimer = setTimeout(() => {
      this.loadPlayerOptions(this.playerSearch);
    }, 260);
  }

  loadTeamAnalytics(): void {
    const teamName = this.selectedTeamName.trim();
    if (!teamName) return;

    this.teamLoading = true;
    this.teamError = '';
    this.api.getTeamAnalytics(teamName, this.currentFilterParams()).subscribe({
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
    if (!this.selectedPlayerId) return;

    this.playerLoading = true;
    this.playerError = '';
    this.api.getPlayerAnalytics(this.selectedPlayerId, this.currentFilterParams()).subscribe({
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

  private loadTeamOptions(): void {
    this.api.getTeamOptions().subscribe({
      next: (teams) => {
        this.teamOptions = teams;
        if (!this.selectedTeamName && teams.length > 0) {
          this.selectedTeamName = teams[0].name;
          this.loadTeamAnalytics();
        }
      },
      error: () => {
        this.teamOptions = [];
      },
    });
  }

  private loadPlayerOptions(query = ''): void {
    this.api.getPlayerOptions(query).subscribe({
      next: (players) => {
        this.playerOptions = players.slice(0, 150);
        if (!this.selectedPlayerId && this.playerOptions.length > 0 && !query.trim()) {
          this.selectedPlayerId = this.playerOptions[0].id;
          this.loadPlayerAnalytics();
        }
      },
      error: () => {
        this.playerOptions = [];
      },
    });
  }

  loadInternationalData(): void {
    this.loadInternationalTeams();
    this.loadInternationalStandings();
    this.loadTopPlayers();
    this.lastUpdatedAt = new Date();
  }

  private loadInternationalTeams(): void {
    this.internationalTeamsLoading = true;
    this.api.getInternationalTeams().subscribe({
      next: (response) => {
        this.internationalTeams = (response.results || [])
          .filter((team) => (team.total_matches || 0) > 0)
          .sort((a, b) => (b.total_matches || 0) - (a.total_matches || 0));
        this.internationalTeamsLoading = false;
      },
      error: () => {
        this.internationalTeams = [];
        this.internationalTeamsLoading = false;
      },
    });
  }

  private loadInternationalStandings(): void {
    this.standingsLoading = true;
    this.api.getInternationalStandings(this.standingsFormat).subscribe({
      next: (response) => {
        this.internationalStandings = response.results;
        this.standingsLoading = false;
      },
      error: () => {
        this.internationalStandings = [];
        this.standingsLoading = false;
      },
    });
  }

  private loadTopPlayers(): void {
    this.topPlayersLoading = true;
    this.api.getTopPlayers(this.topPlayersMetric, 15).subscribe({
      next: (response) => {
        this.topPlayers = response.results;
        this.topPlayersLoading = false;
      },
      error: () => {
        this.topPlayers = [];
        this.topPlayersLoading = false;
      },
    });
  }

  suggestedTeams(): TeamOption[] {
    return this.filteredTeamOptions().slice(0, 2);
  }

  suggestedPlayers(): PlayerOption[] {
    return this.playerOptions.slice(0, 2);
  }

  selectSuggestedTeam(teamName: string): void {
    this.selectedTeamName = teamName;
    this.loadTeamAnalytics();
  }

  selectSuggestedPlayer(playerId: number): void {
    this.selectedPlayerId = playerId;
    this.loadPlayerAnalytics();
  }

  private currentFilterParams(): { format?: string; category?: string } {
    return {
      format: this.formatFilter === 'all' ? undefined : this.formatFilter,
      category: this.categoryFilter === 'all' ? undefined : this.categoryFilter,
    };
  }

  private refreshLoadedAnalytics(): void {
    if (this.selectedTeamName && this.teamAnalytics) {
      this.loadTeamAnalytics();
    }

    if (this.selectedPlayerId && this.playerAnalytics) {
      this.loadPlayerAnalytics();
    }
  }
}
