import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card verify-card">
        <h1>Email Verification</h1>
        <p class="text-secondary" style="margin-top: 0.5rem;">
          Confirming your email token.
        </p>

        <div class="verify-state" *ngIf="loading">
          <div class="loader-dot"></div>
          <span>Verifying your email...</span>
        </div>

        <div class="verify-state success" *ngIf="!loading && success">
          <h3>Verification Complete</h3>
          <p>{{ message }}</p>
          <a routerLink="/auth/login" class="btn btn-primary">Continue to Login</a>
        </div>

        <div class="verify-state error" *ngIf="!loading && !success">
          <h3>Verification Failed</h3>
          <p>{{ message }}</p>
          <a routerLink="/auth/login" class="btn btn-secondary">Back to Login</a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .verify-card {
      max-width: 560px;
      margin: 4rem auto;
      text-align: center;
      border: 1px solid var(--border-primary);
      box-shadow: var(--shadow-primary);
    }

    .verify-state {
      margin-top: 1.5rem;
      display: grid;
      gap: 0.85rem;
      justify-items: center;
      color: var(--text-secondary);
    }

    .verify-state h3 {
      color: var(--text-primary);
      margin-bottom: 0.25rem;
    }

    .verify-state.success h3 {
      color: var(--color-win);
    }

    .verify-state.error h3 {
      color: var(--color-live);
    }

    .loader-dot {
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: var(--color-primary);
      box-shadow: 0 0 0 0 rgba(0, 212, 170, 0.45);
      animation: pulse 1.4s infinite;
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(0, 212, 170, 0.45); }
      70% { box-shadow: 0 0 0 16px rgba(0, 212, 170, 0); }
      100% { box-shadow: 0 0 0 0 rgba(0, 212, 170, 0); }
    }
  `],
})
export class VerifyEmailComponent implements OnInit {
  loading = true;
  success = false;
  message = 'Please wait...';

  constructor(private route: ActivatedRoute, private authService: AuthService) {}

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.loading = false;
      this.success = false;
      this.message = 'Verification token is missing from the URL.';
      return;
    }

    this.authService.confirmEmailVerification(token).subscribe({
      next: (response) => {
        this.loading = false;
        this.success = true;
        this.message = response.detail || 'Your email has been verified successfully.';
      },
      error: (err) => {
        this.loading = false;
        this.success = false;
        this.message = err?.error?.detail || 'The verification link is invalid or expired.';
      },
    });
  }
}
