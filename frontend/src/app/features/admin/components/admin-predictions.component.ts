import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';

import { environment } from '../../../../environments/environment';

interface AdminPredictionJob {
  id: number;
  match_id: number;
  match_name: string;
  requested_by_id: number | null;
  requested_by_email: string;
  prediction_type: 'pre_match' | 'live';
  status: 'pending' | 'processing' | 'complete' | 'failed';
  model_version: string;
  celery_task_id: string;
  error_message: string;
  requested_at: string;
  completed_at: string | null;
  result?: {
    team1: string;
    team2: string;
    team1_win_probability: number;
    team2_win_probability: number;
    draw_probability: number;
    confidence_score: number;
    current_over: number | null;
    current_score: string;
    created_at: string;
  } | null;
}

interface PaginatedAdminPredictionJobs {
  count: number;
  next: string | null;
  previous: string | null;
  results: AdminPredictionJob[];
}

interface BulkActionResponse {
  detail: string;
  action: 'cancel' | 'retry';
  requested: number;
  processed: number;
  skipped: number;
}

interface TeamOption {
  id: number;
  name: string;
  short_name?: string;
  logo_url?: string;
}

@Component({
  selector: 'app-admin-predictions',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <h3>Prediction Jobs</h3>
      <p class="text-secondary" style="margin-top:.5rem;">Monitor, cancel, or retry prediction jobs.</p>

      <div style="margin-top:1rem; display:flex; gap:.5rem; flex-wrap:wrap;">
        <button class="btn btn-secondary" (click)="setStatusFilter('')">All</button>
        <button class="btn btn-secondary" (click)="setStatusFilter('pending')">Pending</button>
        <button class="btn btn-secondary" (click)="setStatusFilter('processing')">Processing</button>
        <button class="btn btn-secondary" (click)="setStatusFilter('complete')">Complete</button>
        <button class="btn btn-secondary" (click)="setStatusFilter('failed')">Failed</button>
      </div>

      <div style="margin-top:.8rem; display:flex; gap:.5rem; flex-wrap:wrap; align-items:center;">
        <button class="btn btn-secondary" [disabled]="selectedJobIds.size === 0" (click)="bulkCancel()">Cancel Selected</button>
        <button class="btn btn-primary" [disabled]="selectedJobIds.size === 0" (click)="bulkRetry()">Retry Selected</button>
        <span class="text-secondary">{{ selectedJobIds.size }} selected</span>
      </div>

      <p *ngIf="message" class="text-secondary" style="margin-top:.8rem;">{{ message }}</p>
      <p *ngIf="error" class="status-error" style="margin-top:.8rem;">{{ error }}</p>

      <div style="margin-top:1rem; overflow:auto;">
        <table style="width:100%; border-collapse:collapse; min-width:980px;">
          <thead style="border-bottom:1px solid #2a3448;">
            <tr style="text-align:left;">
              <th style="padding:.55rem; width:44px;">
                <input
                  type="checkbox"
                  [checked]="areAllVisibleSelected()"
                  (change)="toggleAllVisible($event)"
                  aria-label="Select all visible prediction jobs"
                />
              </th>
              <th style="padding:.55rem;">Job</th>
              <th style="padding:.55rem;">Match</th>
              <th style="padding:.55rem;">
                <button class="btn btn-secondary" (click)="setSorting('prediction_type')">Type {{ sortIndicator('prediction_type') }}</button>
              </th>
              <th style="padding:.55rem;">
                <button class="btn btn-secondary" (click)="setSorting('status')">Status {{ sortIndicator('status') }}</button>
              </th>
              <th style="padding:.55rem;">Requested By</th>
              <th style="padding:.55rem;">
                <button class="btn btn-secondary" (click)="setSorting('requested_at')">Requested At {{ sortIndicator('requested_at') }}</button>
              </th>
              <th style="padding:.55rem;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let job of jobs" style="border-bottom:1px solid #1f2635; cursor:pointer;" (click)="selectJob(job)">
              <td style="padding:.55rem;" (click)="$event.stopPropagation()">
                <input
                  type="checkbox"
                  [checked]="isSelected(job.id)"
                  (change)="toggleSelection(job.id, $event)"
                  [attr.aria-label]="'Select job ' + job.id"
                />
              </td>
              <td style="padding:.55rem;">#{{ job.id }}</td>
              <td style="padding:.55rem;">
                <span style="display:inline-flex; align-items:center; gap:.35rem; flex-wrap:wrap;">
                  <img
                    *ngIf="getLogoForMatchTeam(job.match_name, 0)"
                    [src]="getLogoForMatchTeam(job.match_name, 0) || ''"
                    [alt]="(getMatchTeams(job.match_name)[0] || 'Team') + ' logo'"
                    style="width:16px; height:16px; border-radius:50%; object-fit:cover; border:1px solid var(--border-primary);"
                  />
                  <span>{{ getMatchTeams(job.match_name)[0] || job.match_name }}</span>
                  <span *ngIf="getMatchTeams(job.match_name).length > 1">vs</span>
                  <img
                    *ngIf="getLogoForMatchTeam(job.match_name, 1)"
                    [src]="getLogoForMatchTeam(job.match_name, 1) || ''"
                    [alt]="(getMatchTeams(job.match_name)[1] || 'Team') + ' logo'"
                    style="width:16px; height:16px; border-radius:50%; object-fit:cover; border:1px solid var(--border-primary);"
                  />
                  <span *ngIf="getMatchTeams(job.match_name).length > 1">{{ getMatchTeams(job.match_name)[1] }}</span>
                </span>
              </td>
              <td style="padding:.55rem;">{{ job.prediction_type }}</td>
              <td style="padding:.55rem;">
                <span [style.color]="statusColor(job.status)">{{ job.status }}</span>
              </td>
              <td style="padding:.55rem;">{{ job.requested_by_email || 'system' }}</td>
              <td style="padding:.55rem;">{{ job.requested_at | date:'short' }}</td>
              <td style="padding:.55rem; display:flex; gap:.35rem;">
                <button
                  class="btn btn-secondary"
                  *ngIf="job.status === 'pending' || job.status === 'processing'"
                  (click)="cancelJob(job); $event.stopPropagation()"
                >
                  Cancel
                </button>
                <button
                  class="btn btn-primary"
                  *ngIf="job.status === 'failed'"
                  (click)="retryJob(job); $event.stopPropagation()"
                >
                  Retry
                </button>
              </td>
            </tr>
            <tr *ngIf="jobs.length === 0">
              <td colspan="8" style="padding:1rem;" class="text-secondary">No prediction jobs found.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style="margin-top:1rem; display:flex; gap:.5rem; align-items:center; flex-wrap:wrap;">
        <button class="btn btn-secondary" [disabled]="!hasPreviousPage" (click)="goToPreviousPage()">Previous</button>
        <button class="btn btn-secondary" [disabled]="!hasNextPage" (click)="goToNextPage()">Next</button>
        <span class="text-secondary">Page {{ page }} · {{ totalCount }} total jobs</span>
      </div>

      <div *ngIf="selectedJob" class="card" style="margin-top:1rem; border:1px solid var(--border-primary);">
        <h4>Job #{{ selectedJob.id }} Details</h4>
        <p class="text-secondary" style="margin-top:.4rem;">{{ selectedJob.match_name }} · {{ selectedJob.prediction_type }}</p>

        <div style="margin-top:.8rem; display:grid; gap:.35rem;">
          <div><strong>Status:</strong> <span [style.color]="statusColor(selectedJob.status)">{{ selectedJob.status }}</span></div>
          <div><strong>Model:</strong> {{ selectedJob.model_version }}</div>
          <div><strong>Task ID:</strong> {{ selectedJob.celery_task_id || 'N/A' }}</div>
          <div><strong>Error:</strong> {{ selectedJob.error_message || 'N/A' }}</div>
          <div><strong>Requested:</strong> {{ selectedJob.requested_at | date:'medium' }}</div>
          <div><strong>Completed:</strong> {{ selectedJob.completed_at ? (selectedJob.completed_at | date:'medium') : 'N/A' }}</div>
        </div>

        <div *ngIf="selectedJob.result" style="margin-top:.9rem;">
          <h5 style="margin-bottom:.4rem;">Result Snapshot</h5>
          <div class="text-secondary">
            {{ selectedJob.result.team1 }}: {{ (selectedJob.result.team1_win_probability * 100) | number:'1.0-1' }}%
            · {{ selectedJob.result.team2 }}: {{ (selectedJob.result.team2_win_probability * 100) | number:'1.0-1' }}%
            · Confidence: {{ selectedJob.result.confidence_score | number:'1.0-2' }}
          </div>
          <div class="text-secondary" *ngIf="selectedJob.result.current_score">
            Live Context: {{ selectedJob.result.current_score }} (Over {{ selectedJob.result.current_over ?? 'N/A' }})
          </div>
        </div>
      </div>
    </div>
  `,
})
export class AdminPredictionsComponent implements OnInit {
  jobs: AdminPredictionJob[] = [];
  selectedJob: AdminPredictionJob | null = null;
  private teamLogoByName: Record<string, string> = {};
  statusFilter = '';
  sortBy: 'requested_at' | 'status' | 'prediction_type' = 'requested_at';
  sortDir: 'asc' | 'desc' = 'desc';
  page = 1;
  pageSize = 20;
  totalCount = 0;
  hasNextPage = false;
  hasPreviousPage = false;
  selectedJobIds = new Set<number>();
  message = '';
  error = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadTeamLogos();
    this.loadJobs();
  }

  getMatchTeams(matchName: string): string[] {
    if (!matchName) {
      return [];
    }
    const teams = matchName.split(/\s+vs\s+/i).map((name) => name.trim()).filter(Boolean);
    return teams.slice(0, 2);
  }

  getLogoForMatchTeam(matchName: string, teamIndex: 0 | 1): string | null {
    const teamName = this.getMatchTeams(matchName)[teamIndex];
    if (!teamName) {
      return null;
    }
    return this.teamLogoByName[teamName.toLowerCase()] || null;
  }

  setStatusFilter(status: string): void {
    this.statusFilter = status;
    this.page = 1;
    this.loadJobs();
  }

  setSorting(field: 'requested_at' | 'status' | 'prediction_type'): void {
    if (this.sortBy === field) {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortBy = field;
      this.sortDir = field === 'requested_at' ? 'desc' : 'asc';
    }
    this.page = 1;
    this.loadJobs();
  }

  selectJob(job: AdminPredictionJob): void {
    this.error = '';
    this.http.get<AdminPredictionJob>(`${environment.apiUrl}/admin/prediction-jobs/${job.id}/`).subscribe({
      next: (response) => {
        this.selectedJob = response;
      },
      error: () => {
        this.error = 'Unable to load prediction job details';
      },
    });
  }

  goToNextPage(): void {
    if (!this.hasNextPage) {
      return;
    }
    this.page += 1;
    this.loadJobs();
  }

  goToPreviousPage(): void {
    if (!this.hasPreviousPage || this.page <= 1) {
      return;
    }
    this.page -= 1;
    this.loadJobs();
  }

  isSelected(jobId: number): boolean {
    return this.selectedJobIds.has(jobId);
  }

  toggleSelection(jobId: number, event: Event): void {
    event.stopPropagation();
    if (this.selectedJobIds.has(jobId)) {
      this.selectedJobIds.delete(jobId);
      return;
    }
    this.selectedJobIds.add(jobId);
  }

  areAllVisibleSelected(): boolean {
    return this.jobs.length > 0 && this.jobs.every((job) => this.selectedJobIds.has(job.id));
  }

  toggleAllVisible(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      this.jobs.forEach((job) => this.selectedJobIds.add(job.id));
      return;
    }
    this.jobs.forEach((job) => this.selectedJobIds.delete(job.id));
  }

  cancelJob(job: AdminPredictionJob): void {
    this.message = '';
    this.error = '';
    this.http.post<{ detail: string }>(`${environment.apiUrl}/admin/prediction-jobs/${job.id}/cancel/`, {}).subscribe({
      next: (response) => {
        this.message = response.detail;
        this.loadJobs();
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Failed to cancel prediction job';
      },
    });
  }

  retryJob(job: AdminPredictionJob): void {
    this.message = '';
    this.error = '';
    this.http.post<{ detail: string }>(`${environment.apiUrl}/admin/prediction-jobs/${job.id}/retry/`, {}).subscribe({
      next: (response) => {
        this.message = response.detail;
        this.selectedJobIds.delete(job.id);
        this.loadJobs();
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Failed to retry prediction job';
      },
    });
  }

  bulkCancel(): void {
    this.runBulkAction('cancel');
  }

  bulkRetry(): void {
    this.runBulkAction('retry');
  }

  sortIndicator(field: 'requested_at' | 'status' | 'prediction_type'): string {
    if (this.sortBy !== field) {
      return '';
    }
    return this.sortDir === 'asc' ? '↑' : '↓';
  }

  statusColor(status: string): string {
    switch (status) {
      case 'complete':
        return 'var(--color-win)';
      case 'failed':
        return 'var(--color-live)';
      case 'processing':
        return 'var(--color-accent)';
      default:
        return 'var(--text-secondary)';
    }
  }

  private loadJobs(): void {
    let params = new HttpParams();
    if (this.statusFilter) {
      params = params.set('status', this.statusFilter);
    }
    params = params.set('page', this.page);
    params = params.set('page_size', this.pageSize);
    params = params.set('sort_by', this.sortBy);
    params = params.set('sort_dir', this.sortDir);

    this.http.get<PaginatedAdminPredictionJobs>(`${environment.apiUrl}/admin/prediction-jobs/`, { params }).subscribe({
      next: (response) => {
        this.jobs = response.results;
        this.totalCount = response.count;
        this.hasNextPage = !!response.next;
        this.hasPreviousPage = !!response.previous;

        if (this.selectedJob) {
          const stillVisible = this.jobs.find((job) => job.id === this.selectedJob!.id);
          if (!stillVisible) {
            this.selectedJob = null;
          }
        }
      },
      error: () => {
        this.error = 'Unable to load prediction jobs';
      },
    });
  }

  private runBulkAction(action: 'cancel' | 'retry'): void {
    if (this.selectedJobIds.size === 0) {
      return;
    }

    this.message = '';
    this.error = '';

    this.http
      .post<BulkActionResponse>(`${environment.apiUrl}/admin/prediction-jobs/bulk-action/`, {
        action,
        job_ids: Array.from(this.selectedJobIds),
      })
      .subscribe({
        next: (response) => {
          this.message = `${response.detail}: ${response.processed} processed, ${response.skipped} skipped.`;
          this.selectedJobIds.clear();
          this.loadJobs();
        },
        error: (err) => {
          this.error = err?.error?.detail || 'Bulk action failed';
        },
      });
  }

  private loadTeamLogos(): void {
    this.http.get<TeamOption[]>(`${environment.apiUrl}/auth/team-options/`).subscribe({
      next: (teams) => {
        this.teamLogoByName = teams.reduce((acc, team) => {
          if (team.logo_url) {
            acc[team.name.toLowerCase()] = team.logo_url;
            if (team.short_name) {
              acc[team.short_name.toLowerCase()] = team.logo_url;
            }
          }
          return acc;
        }, {} as Record<string, string>);
      },
      error: () => {
        this.teamLogoByName = {};
      },
    });
  }
}
