import { Component, OnDestroy, OnInit } from '@angular/core';
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
  endpoint_health_history?: Record<string, Array<{ provider: string; path: string; at: string }>>;
}

interface TeamOption {
  id: number;
  name: string;
  short_name?: string;
  logo_url?: string;
}

type PipelineTaskName =
  | 'sync_current_matches'
  | 'sync_cricbuzz_live'
  | 'sync_completed_matches'
  | 'sync_player_stats'
  | 'sync_unified_matches'
  | 'sync_rapidapi_teams'
  | 'sync_rapidapi_players'
  | 'sync_rapidapi_team_logos'
  | 'run_model_retraining_pipeline';

interface EndpointHealthTrendItem {
  key: string;
  latest: { provider: string; path: string; at: string } | null;
  bars: EndpointHealthTrendBar[];
}

type EndpointTrendSort = 'stale_first' | 'most_active' | 'least_active' | 'name';

interface EndpointHealthTrendBar {
  height: number;
  count: number;
  label: string;
}

type PipelineBundleName = 'rapidapi_catalog' | 'match_sync' | 'full_refresh';

interface PipelineBulkTriggerResponse {
  status: string;
  bundle_name: PipelineBundleName;
  queued_count: number;
  tasks: Array<{ task_name: string; task_id: string }>;
}

@Component({
  selector: 'app-admin-pipeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h3>Pipeline Control</h3>
      <p class="text-secondary" style="margin-top:.5rem;">Trigger sync jobs and monitor pipeline counters.</p>

      <div style="margin-top:1rem; border:1px solid var(--border-primary); border-radius:10px; padding:.8rem; background:var(--surface-secondary); display:grid; gap:.55rem;">
        <h4 style="margin:0;">Bulk Pipeline Actions</h4>
        <p class="text-secondary" style="margin:0; font-size:.82rem;">Queue multiple sync tasks in a single click.</p>
        <div style="display:flex; flex-wrap:wrap; gap:.55rem;">
          <button class="btn btn-secondary" [disabled]="bulkRunning" (click)="triggerTaskBundle('rapidapi_catalog')">RapidAPI Catalog Sweep</button>
          <button class="btn btn-secondary" [disabled]="bulkRunning" (click)="triggerTaskBundle('match_sync')">Match Sync Sweep</button>
          <button class="btn btn-primary" [disabled]="bulkRunning" (click)="triggerTaskBundle('full_refresh')">Full Pipeline Refresh</button>
        </div>
        <p *ngIf="bulkStatus" class="text-secondary" style="margin:0; font-size:.82rem;">{{ bulkStatus }}</p>
      </div>

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
            (keydown)="onTeamQueryKeydown($event)"
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
        <p class="text-secondary" style="margin:0; font-size:.78rem;">Team lookup: use ↑/↓ to highlight, Enter to apply.</p>

        <div
          *ngIf="selectedTeam"
          style="display:flex; align-items:center; gap:.55rem; border:1px solid var(--border-primary); border-radius:8px; padding:.45rem .55rem;"
        >
          <img
            *ngIf="selectedTeam.logo_url"
            [src]="selectedTeam.logo_url"
            [alt]="selectedTeam.name + ' logo'"
            style="width:30px; height:30px; border-radius:50%; object-fit:cover; border:1px solid var(--border-primary);"
          />
          <span>
            <strong>{{ selectedTeam.name }}</strong>
            <span class="text-secondary" *ngIf="selectedTeam.short_name">({{ selectedTeam.short_name }})</span>
          </span>
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

      <div *ngIf="endpointHealthTrendEntries.length" style="margin-top:1rem;">
        <h4 style="margin-bottom:.5rem;">Endpoint Health Trends (24h)</h4>
        <div class="text-secondary" style="display:flex; align-items:center; gap:.8rem; margin-bottom:.45rem; font-size:.75rem;">
          <span style="display:inline-flex; align-items:center; gap:.35rem;">
            <span style="width:16px; height:6px; border-radius:4px; background:linear-gradient(90deg, var(--color-accent), #f59e0b);"></span>
            Success count per 3h bucket
          </span>
          <span>Hover bars for bucket time and count</span>
        </div>
        <div style="display:flex; align-items:center; gap:.55rem; flex-wrap:wrap; margin-bottom:.55rem;">
          <button class="btn btn-secondary" (click)="toggleStaleOnly()">
            {{ staleOnly ? 'Show All Endpoints' : 'Show Stale Endpoints Only' }}
          </button>
          <label class="text-secondary" style="font-size:.8rem; display:inline-flex; align-items:center; gap:.35rem;">
            Stale threshold
            <select
              [ngModel]="staleThresholdHours"
              (ngModelChange)="onStaleThresholdChange($event)"
              style="padding:.2rem .4rem; border-radius:6px; border:1px solid var(--border-primary); background:var(--surface-secondary); color:var(--text-primary);"
            >
              <option [ngValue]="3">3h</option>
              <option [ngValue]="6">6h</option>
              <option [ngValue]="12">12h</option>
            </select>
          </label>
          <label class="text-secondary" style="font-size:.8rem; display:inline-flex; align-items:center; gap:.35rem;">
            Sort
            <select
              [ngModel]="endpointSort"
              (ngModelChange)="onEndpointSortChange($event)"
              style="padding:.2rem .4rem; border-radius:6px; border:1px solid var(--border-primary); background:var(--surface-secondary); color:var(--text-primary);"
            >
              <option value="stale_first">Stale First</option>
              <option value="most_active">Most Active</option>
              <option value="least_active">Least Active</option>
              <option value="name">Name</option>
            </select>
          </label>
          <span class="text-secondary" style="font-size:.8rem;">
            Stale: {{ staleEndpointCount }} / {{ allEndpointHealthTrendEntries.length }}
          </span>
        </div>
        <div style="display:grid; grid-template-columns:minmax(140px, 1fr) 110px minmax(220px, 1fr); gap:.7rem; align-items:center; margin-bottom:.55rem; border:1px solid var(--border-primary); border-radius:10px; padding:.5rem; background:var(--surface-secondary);">
          <div>
            <strong>All Endpoints</strong>
            <div class="text-secondary" style="font-size:.75rem;">{{ allEndpointHealthTrendEntries.length }} tracked endpoints</div>
          </div>
          <div class="text-secondary" style="font-size:.78rem;">{{ aggregateSuccessCount }} successes / 24h</div>
          <div style="height:34px; display:grid; grid-template-columns:repeat(8, 1fr); align-items:end; gap:.2rem; border:1px solid var(--border-primary); border-radius:8px; padding:.25rem; background:var(--surface-primary);">
            <span
              *ngFor="let bar of aggregateEndpointTrendBars"
              [style.height.%]="bar.height"
              [attr.title]="bar.label + ' - ' + bar.count + ' successes'"
              style="display:block; border-radius:3px; background:linear-gradient(180deg, #22c55e, #16a34a); min-height:3px;"
            ></span>
          </div>
        </div>
        <div style="display:grid; gap:.55rem;">
          <div
            *ngFor="let item of endpointHealthTrendEntries"
            style="display:grid; grid-template-columns:minmax(140px, 1fr) 110px minmax(220px, 1fr); gap:.7rem; align-items:center;"
          >
            <div>
              <strong>{{ item.key }}</strong>
              <div class="text-secondary" style="font-size:.75rem;">
                {{ item.latest?.provider || 'unknown' }}
                <span *ngIf="item.latest">· {{ item.latest.at | date:'short' }}</span>
                <span *ngIf="isStale(item)" style="color:var(--color-accent);"> · stale</span>
              </div>
            </div>
            <div class="text-secondary" style="font-size:.78rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ item.latest?.path || 'No success yet' }}</div>
            <div style="height:34px; display:grid; grid-template-columns:repeat(8, 1fr); align-items:end; gap:.2rem; border:1px solid var(--border-primary); border-radius:8px; padding:.25rem; background:var(--surface-secondary);">
              <span
                *ngFor="let bar of item.bars"
                [style.height.%]="bar.height"
                [attr.title]="bar.label + ' - ' + bar.count + ' successes'"
                style="display:block; border-radius:3px; background:linear-gradient(180deg, var(--color-accent), #f59e0b); min-height:3px;"
              ></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class AdminPipelineComponent implements OnInit, OnDestroy {
  private static readonly TEAM_ID_STORAGE_KEY = 'admin_pipeline.players_team_id';
  private static readonly STALE_ONLY_STORAGE_KEY = 'admin_pipeline.endpoint_trends.stale_only';
  private static readonly STALE_THRESHOLD_STORAGE_KEY = 'admin_pipeline.endpoint_trends.stale_threshold_hours';
  private static readonly ENDPOINT_SORT_STORAGE_KEY = 'admin_pipeline.endpoint_trends.sort';

  status: PipelineStatusSnapshot | null = null;
  filteredTeams: TeamOption[] = [];
  teamQuery = '';
  selectedLookupTeamId: number | null = null;
  playersTeamId: number | null = null;
  highlightedTeamIndex = -1;
  bulkRunning = false;
  bulkStatus = '';
  staleOnly = false;
  staleThresholdHours = 6;
  endpointSort: EndpointTrendSort = 'stale_first';
  private statusRefreshTimer: ReturnType<typeof setInterval> | null = null;
  private teamSearchTimer: ReturnType<typeof setTimeout> | null = null;
  message = '';
  error = '';

  get endpointHealthEntries(): Array<{ key: string; value: { provider: string; path: string; at: string } }> {
    const health = this.status?.endpoint_health || {};
    return Object.entries(health).map(([key, value]) => ({ key, value }));
  }

  get selectedTeam(): TeamOption | null {
    if (!this.playersTeamId) {
      return null;
    }
    return this.filteredTeams.find((team) => team.id === this.playersTeamId) || null;
  }

  get endpointHealthTrendEntries(): EndpointHealthTrendItem[] {
    let entries = [...this.allEndpointHealthTrendEntries];
    entries = this.sortEndpointTrendEntries(entries);

    if (!this.staleOnly) {
      return entries;
    }
    return entries.filter((item) => this.isStale(item));
  }

  get allEndpointHealthTrendEntries(): EndpointHealthTrendItem[] {
    const latest = this.status?.endpoint_health || {};
    const history = this.status?.endpoint_health_history || {};
    const keys = Array.from(new Set([...Object.keys(latest), ...Object.keys(history)])).sort();

    return keys.map((key) => {
      const events = Array.isArray(history[key]) ? history[key] : [];
      return {
        key,
        latest: latest[key] || events[events.length - 1] || null,
        bars: this.buildTrendBars(events),
      };
    });
  }

  get aggregateEndpointTrendBars(): EndpointHealthTrendBar[] {
    const history = this.status?.endpoint_health_history || {};
    const allEvents = Object.values(history)
      .filter((events): events is Array<{ provider: string; path: string; at: string }> => Array.isArray(events))
      .flat();
    return this.buildTrendBars(allEvents);
  }

  get aggregateSuccessCount(): number {
    return this.aggregateEndpointTrendBars.reduce((sum, bar) => sum + bar.count, 0);
  }

  get staleEndpointCount(): number {
    return this.allEndpointHealthTrendEntries.filter((item) => this.isStale(item)).length;
  }

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.restoreSelectedTeamId();
    this.restoreTrendPreferences();
    this.fetchTeams('');
    this.loadStatus();
    this.statusRefreshTimer = setInterval(() => this.loadStatus(), 20000);
  }

  ngOnDestroy(): void {
    if (this.statusRefreshTimer) {
      clearInterval(this.statusRefreshTimer);
      this.statusRefreshTimer = null;
    }

    if (this.teamSearchTimer) {
      clearTimeout(this.teamSearchTimer);
      this.teamSearchTimer = null;
    }
  }

  onTeamQueryChange(): void {
    this.highlightedTeamIndex = -1;

    if (this.teamSearchTimer) {
      clearTimeout(this.teamSearchTimer);
    }

    this.teamSearchTimer = setTimeout(() => {
      this.fetchTeams(this.teamQuery);
    }, 280);
  }

  onTeamQueryKeydown(event: KeyboardEvent): void {
    if (this.filteredTeams.length === 0) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.highlightedTeamIndex = this.getNextIndex(1);
      this.syncHighlightedToSelection();
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.highlightedTeamIndex = this.getNextIndex(-1);
      this.syncHighlightedToSelection();
      return;
    }

    if (event.key === 'Enter') {
      if (this.highlightedTeamIndex >= 0 && this.highlightedTeamIndex < this.filteredTeams.length) {
        event.preventDefault();
        this.applyHighlightedTeam();
      }
      return;
    }

    if (event.key === 'Escape') {
      this.highlightedTeamIndex = -1;
    }
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

  toggleStaleOnly(): void {
    this.staleOnly = !this.staleOnly;
    localStorage.setItem(AdminPipelineComponent.STALE_ONLY_STORAGE_KEY, this.staleOnly ? '1' : '0');
  }

  onStaleThresholdChange(value: number): void {
    const numeric = Number(value);
    if (![3, 6, 12].includes(numeric)) {
      return;
    }
    this.staleThresholdHours = numeric;
    localStorage.setItem(AdminPipelineComponent.STALE_THRESHOLD_STORAGE_KEY, String(numeric));
  }

  onEndpointSortChange(value: EndpointTrendSort): void {
    if (!['stale_first', 'most_active', 'least_active', 'name'].includes(value)) {
      return;
    }
    this.endpointSort = value;
    localStorage.setItem(AdminPipelineComponent.ENDPOINT_SORT_STORAGE_KEY, value);
  }

  triggerTask(task_name: PipelineTaskName): void {
    this.message = '';
    this.error = '';

    this.triggerTaskRequest(task_name)
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

  triggerTaskBundle(bundleName: PipelineBundleName): void {
    if (this.bulkRunning) {
      return;
    }

    this.bulkRunning = true;
    this.bulkStatus = `Queueing bundle: ${bundleName}`;
    this.message = '';
    this.error = '';

    this.triggerBulkBundleRequest(bundleName).subscribe({
      next: (response) => {
        this.bulkRunning = false;
        this.bulkStatus = '';
        this.message = `Bundle queued: ${response.bundle_name} (${response.queued_count} tasks)`;
        this.loadStatus();
      },
      error: (err) => {
        this.bulkRunning = false;
        this.bulkStatus = '';
        this.error = err?.error?.detail || 'Failed to trigger pipeline bundle';
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
            const selectedIndex = this.filteredTeams.findIndex((team) => team.id === selected.id);
            this.highlightedTeamIndex = selectedIndex;
            return;
          }
        }

        this.highlightedTeamIndex = this.filteredTeams.length > 0 ? 0 : -1;
      },
      error: () => {
        this.error = this.error || 'Unable to load team options for lookup';
      },
    });
  }

  private getNextIndex(direction: 1 | -1): number {
    if (this.filteredTeams.length === 0) {
      return -1;
    }

    if (this.highlightedTeamIndex < 0) {
      return direction === 1 ? 0 : this.filteredTeams.length - 1;
    }

    const next = this.highlightedTeamIndex + direction;
    if (next < 0) {
      return this.filteredTeams.length - 1;
    }
    if (next >= this.filteredTeams.length) {
      return 0;
    }
    return next;
  }

  private syncHighlightedToSelection(): void {
    if (this.highlightedTeamIndex < 0 || this.highlightedTeamIndex >= this.filteredTeams.length) {
      return;
    }

    this.selectedLookupTeamId = this.filteredTeams[this.highlightedTeamIndex].id;
  }

  private applyHighlightedTeam(): void {
    if (this.highlightedTeamIndex < 0 || this.highlightedTeamIndex >= this.filteredTeams.length) {
      return;
    }

    const selected = this.filteredTeams[this.highlightedTeamIndex];
    this.onTeamSelect(selected.id);
  }

  private triggerTaskRequest(task_name: PipelineTaskName) {
    const payload: { task_name: PipelineTaskName; team_id?: number } = { task_name };
    if (task_name === 'sync_rapidapi_players' && this.playersTeamId && this.playersTeamId > 0) {
      payload.team_id = this.playersTeamId;
    }

    return this.http.post<{ status: string; task_name: string; task_id: string }>(
      `${environment.apiUrl}/admin/pipeline/trigger/`,
      payload
    );
  }

  private triggerBulkBundleRequest(bundle_name: PipelineBundleName) {
    const payload: { bundle_name: PipelineBundleName; team_id?: number } = { bundle_name };
    if (this.playersTeamId && this.playersTeamId > 0) {
      payload.team_id = this.playersTeamId;
    }

    return this.http.post<PipelineBulkTriggerResponse>(
      `${environment.apiUrl}/admin/pipeline/trigger-bulk/`,
      payload
    );
  }

  private buildTrendBars(events: Array<{ provider: string; path: string; at: string }>): EndpointHealthTrendBar[] {
    const { counts, labels } = this.buildTrendBucketData(events);

    const max = Math.max(...counts);
    if (max === 0) {
      return counts.map((count, index) => ({
        height: 10,
        count,
        label: labels[index],
      }));
    }
    return counts.map((value, index) => ({
      height: value === 0 ? 10 : Math.max(20, Math.round((value / max) * 100)),
      count: value,
      label: labels[index],
    }));
  }

  private buildTrendBucketData(
    events: Array<{ provider: string; path: string; at: string }>
  ): { counts: number[]; labels: string[] } {
    const bucketCount = 8;
    const windowMs = 24 * 60 * 60 * 1000;
    const bucketMs = windowMs / bucketCount;
    const now = Date.now();
    const windowStart = now - windowMs;
    const counts = new Array<number>(bucketCount).fill(0);

    for (const event of events) {
      const ts = Date.parse(event.at);
      if (Number.isNaN(ts) || ts < windowStart || ts > now) {
        continue;
      }
      const offset = ts - windowStart;
      const index = Math.min(bucketCount - 1, Math.max(0, Math.floor(offset / bucketMs)));
      counts[index] += 1;
    }

    return {
      counts,
      labels: this.buildBucketLabels(windowStart, bucketMs, bucketCount),
    };
  }

  private buildBucketLabels(windowStart: number, bucketMs: number, bucketCount: number): string[] {
    const labels: string[] = [];
    for (let index = 0; index < bucketCount; index += 1) {
      const start = new Date(windowStart + index * bucketMs);
      const end = new Date(windowStart + (index + 1) * bucketMs);
      const startLabel = start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const endLabel = end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      labels.push(`${startLabel} to ${endLabel}`);
    }
    return labels;
  }

  isStale(item: EndpointHealthTrendItem): boolean {
    if (!item.latest?.at) {
      return true;
    }
    const timestamp = Date.parse(item.latest.at);
    if (Number.isNaN(timestamp)) {
      return true;
    }
    const staleAfterMs = this.staleThresholdHours * 60 * 60 * 1000;
    return Date.now() - timestamp > staleAfterMs;
  }

  private sortEndpointTrendEntries(entries: EndpointHealthTrendItem[]): EndpointHealthTrendItem[] {
    if (this.endpointSort === 'most_active') {
      return entries.sort((left, right) => this.getActivityScore(right) - this.getActivityScore(left));
    }
    if (this.endpointSort === 'least_active') {
      return entries.sort((left, right) => this.getActivityScore(left) - this.getActivityScore(right));
    }
    if (this.endpointSort === 'name') {
      return entries.sort((left, right) => left.key.localeCompare(right.key));
    }

    return entries.sort((left, right) => {
      const leftStale = this.isStale(left) ? 1 : 0;
      const rightStale = this.isStale(right) ? 1 : 0;
      if (leftStale !== rightStale) {
        return rightStale - leftStale;
      }
      return this.getActivityScore(right) - this.getActivityScore(left);
    });
  }

  private getActivityScore(item: EndpointHealthTrendItem): number {
    return item.bars.reduce((sum, bar) => sum + bar.count, 0);
  }

  private restoreTrendPreferences(): void {
    const staleOnlyRaw = localStorage.getItem(AdminPipelineComponent.STALE_ONLY_STORAGE_KEY);
    if (staleOnlyRaw === '1' || staleOnlyRaw === '0') {
      this.staleOnly = staleOnlyRaw === '1';
    }

    const thresholdRaw = Number(localStorage.getItem(AdminPipelineComponent.STALE_THRESHOLD_STORAGE_KEY));
    if ([3, 6, 12].includes(thresholdRaw)) {
      this.staleThresholdHours = thresholdRaw;
    }

    const sortRaw = localStorage.getItem(AdminPipelineComponent.ENDPOINT_SORT_STORAGE_KEY);
    if (sortRaw && ['stale_first', 'most_active', 'least_active', 'name'].includes(sortRaw)) {
      this.endpointSort = sortRaw as EndpointTrendSort;
    }
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
