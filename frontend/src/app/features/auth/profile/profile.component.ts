import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../core/models';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <section class="card" style="margin-bottom:1rem;">
        <h1>My Profile</h1>
        <p class="text-secondary" style="margin-top:.45rem;">Your account details and password settings.</p>
      </section>

      <section class="card" style="margin-bottom:1rem;">
        <h3>Profile Data</h3>
        <p *ngIf="loading" class="text-secondary" style="margin-top:.55rem;">Loading profile...</p>
        <p *ngIf="error" class="status-error" style="margin-top:.55rem;">{{ error }}</p>

        <div *ngIf="profile" style="margin-top:.75rem; display:grid; gap:.55rem;">
          <p><strong>Username:</strong> {{ profile.username }}</p>
          <p><strong>Email:</strong> {{ profile.email }}</p>
          <p><strong>Role:</strong> {{ profile.role }}</p>
          <p><strong>Email Status:</strong> {{ profile.email_verified ? 'Verified' : 'Not verified' }}</p>
          <p *ngIf="profile.bio"><strong>Bio:</strong> {{ profile.bio }}</p>
        </div>
      </section>

      <section class="card">
        <h3>Change Password</h3>
        <p class="text-secondary" style="margin-top:.35rem;">Use a strong password with at least 8 characters.</p>

        <div style="margin-top:.75rem; display:grid; gap:.65rem; max-width:520px;">
          <label>
            <span class="text-secondary" style="display:block; margin-bottom:.25rem;">Current Password</span>
            <input class="input" type="password" [(ngModel)]="currentPassword" />
          </label>

          <label>
            <span class="text-secondary" style="display:block; margin-bottom:.25rem;">New Password</span>
            <input class="input" type="password" [(ngModel)]="newPassword" />
          </label>

          <label>
            <span class="text-secondary" style="display:block; margin-bottom:.25rem;">Confirm New Password</span>
            <input class="input" type="password" [(ngModel)]="confirmPassword" />
          </label>
        </div>

        <p *ngIf="passwordError" class="status-error" style="margin-top:.7rem;">{{ passwordError }}</p>
        <p *ngIf="passwordSuccess" class="text-secondary" style="margin-top:.7rem; color:var(--color-win);">{{ passwordSuccess }}</p>

        <div style="margin-top:.9rem; display:flex; gap:.55rem; flex-wrap:wrap;">
          <button class="btn btn-primary" [disabled]="changingPassword" (click)="changePassword()">
            {{ changingPassword ? 'Updating...' : 'Update Password' }}
          </button>
        </div>
      </section>
    </div>
  `,
})
export class ProfileComponent implements OnInit {
  profile: User | null = null;
  loading = false;
  error = '';

  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  changingPassword = false;
  passwordError = '';
  passwordSuccess = '';

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.loading = true;
    this.auth.loadProfile().subscribe({
      next: (profile) => {
        this.profile = profile;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        if (err?.status === 401) {
          this.auth.logout();
          this.router.navigate(['/auth/login']);
          return;
        }
        this.error = 'Unable to load profile right now.';
      },
    });
  }

  changePassword(): void {
    this.passwordError = '';
    this.passwordSuccess = '';

    if (!this.currentPassword || !this.newPassword || !this.confirmPassword) {
      this.passwordError = 'Please fill all password fields.';
      return;
    }

    if (this.newPassword.length < 8) {
      this.passwordError = 'New password must be at least 8 characters.';
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.passwordError = 'New password and confirmation do not match.';
      return;
    }

    this.changingPassword = true;
    this.auth.changePassword(this.currentPassword, this.newPassword).subscribe({
      next: (res) => {
        this.changingPassword = false;
        this.passwordSuccess = res.detail || 'Password updated successfully.';
        this.currentPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
      },
      error: (err) => {
        this.changingPassword = false;
        this.passwordError = err?.error?.detail || err?.error?.current_password?.[0] || 'Unable to update password right now.';
      },
    });
  }
}
