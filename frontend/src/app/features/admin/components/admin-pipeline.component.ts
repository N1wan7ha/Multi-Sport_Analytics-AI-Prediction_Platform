import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { environment } from '../../../../environments/environment';

interface PipelineStatusSnapshot {
  current_matches: number;
  live_matches: number;
  completed_matches: number;
  player_stats: number;
  unified_matches: number;
  last_model_retraining: string;
  endpoint_health?: Record<string, { provider: string; path: string; at: string }>;
}

interface TeamOption {
  id: number;
  name: string;
  short_name?: string;
}

@Component({
  selector: 'app-admin-pipeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h3>Pipeline Control</h3>
      <p class="text-secondary" style="margin-top:.5rem;">Trigger sync jobs and monitor pipeline counters.</p>

      <div style="margin-top:1rem; display:grid; gap:.65rem; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));">
        <button class="btn btn-secondary" (click)="triggerTask('sync_current_matches')">Sync Current Matches</button>
        <button class="btn btn-secondary" (click)="triggerTask('sync_cricbuzz_live')">Sync Live Matches</button>
        <button class="btn btn-secondary" (click)="triggerTask('sync_completed_matches')">Sync Completed Matches</button>
        <button class="btn btn-secondary" (click)="triggerTask('sync_player_stats')">Sync Player Stats</button>
        <button class="btn btn-secondary" (click)="triggerTask('sync_rapidapi_teams')">Sync Teams Catalog</button>
        <div style="display:flex; gap:.45rem; align-items:center; flex-wrap:wrap;">
          <input
            type="text"
            [(ngModel)]="teamQuery"
            (ngModelChange)="onTeamQueryChange()"
            placeholder="search team"
            style="min-width:180px; max-width:220px; padding:.45rem .55rem; border-radius:8px; border:1px solid var(--border-primary); background:var(--surface-secondary); color:var(--text-primary);"
          />
          <select
            [ngModel]="selectedLookupTeamId"
            (ngModelChange)="onTeamSelect($event)"
            style="min-width:180px; max-width:230px; padding:.45rem .55rem; border-radius:8px; border:1px solid var(--border-primary); background:var(--surface-secondary); color:var(--text-primary);"
          >
            <option [ngValue]="null">Select team</option>
            <option *ngFor="let team of filteredTeams" [ngValue]="team.id">
              {{ team.name }}{{ team.short_name ? ' (' + team.short_name + ')' : '' }}
            </option>
          </select>
          <input
            type="number"
            min="1"
            [(ngModel)]="playersTeamId"
            (ngModelChange)="onTeamIdChange($event)"
            placeholder="team id"
            style="max-width:120px; padding:.45rem .55rem; border-radius:8px; border:1px solid var(--border-primary); background:var(--surface-secondary); color:var(--text-primary);"
          />
          <button class="btn btn-secondary" (click)="triggerTask('sync_rapidapi_players')">Sync Players Catalog</button>
        </div>
        <button class="btn btn-secondary" (click)="triggerTask('sync_rapidapi_team_logos')">Sync Team Logos</button>
        <button class="btn btn-secondary" (click)="triggerTask('sync_unified_matches')">Run Unified Sync</button>
        <button class="btn btn-primary" (click)="triggerTask('run_model_retraining_pipeline')">Run Retraining</button>
      </div>

      <p *ngIf="message" class="text-secondary" style="margin-top:.8rem;">{{ message }}</p>
      <p *ngIf="error" class="status-error" style="margin-top:.8rem;">{{ error }}</p>

      <div *ngIf="status" style="margin-top:1rem; display:grid; gap:.5rem;">
        <div class="list-row"><strong>Current matches:</strong> {{ status.current_matches }}</div>
        <div class="list-row"><strong>Live matches:</strong> {{ status.live_matches }}</div>
        <div class="list-row"><strong>Completed matches:</strong> {{ status.completed_matches }}</div>
        <div class="list-row"><strong>Player stats:</strong> {{ status.player_stats }}</div>
        <div class="list-row"><strong>Unified matches:</strong> {{ status.unified_matches }}</div>
        <div class="list-row"><strong>Last retraining:</strong> {{ status.last_model_retraining || 'N/A' }}</div>
      </div>

      <div *ngIf="endpointHealthEntries.length" style="margin-top:1rem;">
        <h4 style="margin-bottom:.5rem;">Endpoint Health</h4>
        <div style="display:grid; gap:.45rem;">
          <div class="list-row" *ngFor="let item of endpointHealthEntries">
            <strong>{{ item.key }}:</strong>
            {{ item.value.provider }} → {{ item.value.path }}
            <span class="text-secondary">({{ item.value.at | date:'short' }})</span>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class AdminPipelineComponent implements OnInit {
  private static readonly TEAM_ID_STORAGE_KEY = 'admin_pipeline.players_team_id';

  status: PipelineStatusSnapshot | null = null;
  filteredTeams: TeamOption[] = [];
  teamQuery = '';
  selectedLookupTeamId: number | null = null;
  playersTeamId: number | null = null;
  private teamSearchTimer: ReturnType<typeof setTimeout> | null = null;
  message = '';
  error = '';

  get endpointHealthEntries(): Array<{ key: string; value: { provider: string; path: string; at: string } }> {
    const health = this.status?.endpoint_health || {};
    return Object.entries(health).map(([key, value]) => ({ key, value }));
  }

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.restoreSelectedTeamId();
    this.fetchTeams('');
    this.loadStatus();
  }

  onTeamQueryChange(): void {
    if (this.teamSearchTimer) {
      clearTimeout(this.teamSearchTimer);
    }

    this.teamSearchTimer = setTimeout(() => {
      this.fetchTeams(this.teamQuery);
    }, 280);
  }

  onTeamSelect(teamId: number | null): void {
    this.selectedLookupTeamId = teamId;
    this.playersTeamId = teamId;
    this.persistSelectedTeamId();
  }

  onTeamIdChange(teamId: number | null): void {
    if (teamId === null || teamId === undefined || Number.isNaN(Number(teamId))) {
      this.playersTeamId = null;
      this.selectedLookupTeamId = null;
      this.persistSelectedTeamId();
      return;
    }

    const normalized = Number(teamId);
    this.playersTeamId = normalized > 0 ? normalized : null;
    this.selectedLookupTeamId = this.playersTeamId;
    this.persistSelectedTeamId();
  }

  triggerTask(task_name: string): void {
    this.message = '';
    this.error = '';

    const payload: { task_name: string; team_id?: number } = { task_name };
    if (task_name === 'sync_rapidapi_players' && this.playersTeamId && this.playersTeamId > 0) {
      payload.team_id = this.playersTeamId;
    }

    this.http
      .post<{ status: string; task_name: string; task_id: string }>(`${environment.apiUrl}/admin/pipeline/trigger/`, payload)
      .subscribe({
        next: (response) => {
          this.message = `Task queued: ${response.task_name} (${response.task_id})`;
          this.loadStatus();
        },
        error: (err) => {
          this.error = err?.error?.detail || 'Failed to trigger pipeline task';
        },
      });
  }

  private loadStatus(): void {
    this.http.get<PipelineStatusSnapshot>(`${environment.apiUrl}/admin/pipeline/status/`).subscribe({
      next: (response) => {
        this.status = response;
      },
      error: () => {
        this.error = 'Unable to load pipeline status';
      },
    });
  }

  private fetchTeams(query: string): void {
    const q = query.trim();
    const url = q
      ? `${environment.apiUrl}/auth/team-options/?q=${encodeURIComponent(q)}`
      : `${environment.apiUrl}/auth/team-options/`;

    this.http.get<TeamOption[]>(url).subscribe({
      next: (response) => {
        this.filteredTeams = response.slice(0, 60);
        if (this.playersTeamId) {
          const selected = this.filteredTeams.find((team) => team.id === this.playersTeamId);
          if (selected) {
            this.selectedLookupTeamId = selected.id;
          }
        }
      },
      error: () => {
        this.error = this.error || 'Unable to load team options for lookup';
      },
    });
  }

  private restoreSelectedTeamId(): void {
    const raw = localStorage.getItem(AdminPipelineComponent.TEAM_ID_STORAGE_KEY);
    if (!raw) {
      return;
    }

    const parsed = Number(raw);
    if (!Number.isNaN(parsed) && parsed > 0) {
      this.playersTeamId = parsed;
      this.selectedLookupTeamId = parsed;
    }
  }

  private persistSelectedTeamId(): void {
    if (this.playersTeamId && this.playersTeamId > 0) {
      localStorage.setItem(AdminPipelineComponent.TEAM_ID_STORAGE_KEY, String(this.playersTeamId));
      return;
    }
    localStorage.removeItem(AdminPipelineComponent.TEAM_ID_STORAGE_KEY);
  }
}
