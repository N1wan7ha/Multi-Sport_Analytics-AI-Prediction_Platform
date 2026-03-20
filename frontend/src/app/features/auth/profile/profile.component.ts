import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, PredictionHistoryEntry, TeamOption } from '../../../core/services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card" style="margin-bottom:1rem;">
        <h1>Profile</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Manage favourite teams and view your prediction history.</p>
      </div>

      <div class="card" style="margin-bottom:1rem;">
        <h3>Email Verification</h3>
        <p class="text-secondary" style="margin-top:0.5rem;">
          Keep your account secure by verifying your email address.
        </p>

        <div style="margin-top:0.85rem; display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
          <span
            [style.color]="emailVerified ? 'var(--color-win)' : 'var(--color-accent)'"
            [style.border]="emailVerified ? '1px solid rgba(16,185,129,0.35)' : '1px solid rgba(245,158,11,0.35)'"
            style="padding:0.28rem 0.55rem; border-radius:999px; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.06em;"
          >
            {{ emailVerified ? 'Verified' : 'Not Verified' }}
          </span>

          <button
            class="btn btn-secondary"
            *ngIf="emailVerified === false"
            [disabled]="resendingVerification"
            (click)="resendVerificationEmail()"
          >
            {{ resendingVerification ? 'Sending...' : 'Resend Verification Email' }}
          </button>
        </div>

        <p class="text-secondary" *ngIf="verificationMessage" style="margin-top:0.7rem;">{{ verificationMessage }}</p>
        <p class="status-error" *ngIf="verificationError" style="margin-top:0.7rem;">{{ verificationError }}</p>
      </div>

      <div class="card" style="margin-bottom:1rem;">
        <h3>Favourite Teams</h3>
        <p *ngIf="loadingTeams" class="text-secondary">Loading teams...</p>
        <p *ngIf="error" class="status-error">{{ error }}</p>

        <div *ngIf="!loadingTeams" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.5rem; margin-top:.75rem;">
          <label *ngFor="let team of teams" style="display:flex; align-items:center; gap:.5rem;">
            <input type="checkbox" [checked]="selectedTeamIds.has(team.id)" (change)="toggleTeam(team.id, $event)" />
            <span>{{ team.name }}</span>
          </label>
        </div>

        <div style="margin-top:1rem; display:flex; gap:.5rem;">
          <button class="btn btn-primary" (click)="saveFavourites()" [disabled]="savingFavourites">{{ savingFavourites ? 'Saving...' : 'Save Favourites' }}</button>
        </div>
      </div>

      <div class="card">
        <h3>Prediction History</h3>
        <p *ngIf="loadingHistory" class="text-secondary">Loading history...</p>
        <p *ngIf="!loadingHistory && history.length === 0" class="text-secondary">No prediction history yet.</p>

        <div *ngFor="let item of history" class="list-row" style="display:grid; gap:.3rem;">
          <div><strong>{{ item.match_name }}</strong> · {{ item.prediction_type }}</div>
          <div class="text-secondary">Status: {{ item.status }} · Model: {{ item.model_version }}</div>
          <div *ngIf="item.result" class="text-secondary">
            T1 {{ (item.result.team1_win_probability * 100) | number:'1.0-1' }}%
            · T2 {{ (item.result.team2_win_probability * 100) | number:'1.0-1' }}%
            · Confidence {{ item.result.confidence_score | number:'1.0-2' }}
          </div>
        </div>
      </div>
    </div>
  `,
})
export class ProfileComponent implements OnInit {
  teams: TeamOption[] = [];
  history: PredictionHistoryEntry[] = [];
  selectedTeamIds = new Set<number>();
  emailVerified = false;
  loadingTeams = false;
  loadingHistory = false;
  savingFavourites = false;
  resendingVerification = false;
  verificationMessage = '';
  verificationError = '';
  error = '';

  constructor(private auth: AuthService) {}

  ngOnInit(): void {
    this.loadProfileData();
  }

  private loadProfileData(): void {
    this.loadingTeams = true;
    this.loadingHistory = true;

    this.auth.loadProfile().subscribe({
      next: (profile) => {
        this.selectedTeamIds = new Set((profile.favourite_teams || []).map((team) => team.id));
        this.emailVerified = !!profile.email_verified;
      },
      error: () => {
        this.error = 'Failed to load profile.';
      },
    });

    this.auth.getTeamOptions().subscribe({
      next: (teams) => {
        this.teams = teams;
        this.loadingTeams = false;
      },
      error: () => {
        this.loadingTeams = false;
        this.error = 'Failed to load teams.';
      },
    });

    this.auth.getPredictionHistory().subscribe({
      next: (response) => {
        this.history = response.results;
        this.loadingHistory = false;
      },
      error: () => {
        this.loadingHistory = false;
        this.error = 'Failed to load prediction history.';
      },
    });
  }

  toggleTeam(teamId: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      this.selectedTeamIds.add(teamId);
    } else {
      this.selectedTeamIds.delete(teamId);
    }
  }

  saveFavourites(): void {
    this.savingFavourites = true;
    this.error = '';
    const ids = Array.from(this.selectedTeamIds.values());

    this.auth.updateProfile({ favourite_team_ids: ids }).subscribe({
      next: (updated) => {
        this.selectedTeamIds = new Set((updated.favourite_teams || []).map((team) => team.id));
        this.savingFavourites = false;
      },
      error: () => {
        this.savingFavourites = false;
        this.error = 'Unable to save favourites right now.';
      },
    });
  }

  resendVerificationEmail(): void {
    if (this.emailVerified) {
      return;
    }

    this.resendingVerification = true;
    this.verificationMessage = '';
    this.verificationError = '';

    this.auth.resendEmailVerification().subscribe({
      next: (response) => {
        this.resendingVerification = false;
        this.verificationMessage = response.detail || 'Verification email sent.';
      },
      error: (err) => {
        this.resendingVerification = false;
        this.verificationError = err?.error?.detail || 'Failed to send verification email.';
      },
    });
  }
}
