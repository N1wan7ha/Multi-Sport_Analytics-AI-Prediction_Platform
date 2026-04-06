import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Register</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Create a MatchMind account.</p>

        <div style="margin-top:1rem; display:grid; gap:.75rem; max-width:420px;">
          <input class="input" type="email" [(ngModel)]="email" placeholder="Email" />
          <input class="input" type="text" [(ngModel)]="username" placeholder="Username" />
          <input class="input" type="password" [(ngModel)]="password" placeholder="Password" />
          <button class="btn btn-primary" (click)="register()" [disabled]="loading">
            {{ loading ? 'Creating account...' : 'Create account' }}
          </button>
          <div style="display:flex; align-items:center; gap:.5rem; margin: .25rem 0;">
            <span style="height:1px; flex:1; background:#d9d9d9;"></span>
            <span class="text-secondary" style="font-size:.85rem;">or</span>
            <span style="height:1px; flex:1; background:#d9d9d9;"></span>
          </div>
          <div id="google-register-btn" style="min-height:40px;"></div>
          <p *ngIf="message" class="text-secondary">{{ message }}</p>
          <p *ngIf="error" style="color:#d83a52;">{{ error }}</p>
          <a routerLink="/auth/login" class="text-secondary">Already have an account? Login</a>
          <a routerLink="/auth/profile" class="text-secondary">Go to profile</a>
        </div>
      </div>
    </div>
  `,
})
export class RegisterComponent implements OnInit {
  email = '';
  username = '';
  password = '';
  loading = false;
  message = '';
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.initializeGoogleButton();
  }

  register(): void {
    if (!this.email || !this.username || !this.password) return;
    this.loading = true;
    this.message = '';
    this.error = '';

    this.auth.register(this.email, this.username, this.password).subscribe({
      next: () => {
        this.loading = false;
        this.message = 'Account created. Check your email for verification, then login.';
        setTimeout(() => this.router.navigate(['/auth/login']), 700);
      },
      error: () => {
        this.loading = false;
        this.error = 'Registration failed. Try a different email/username.';
      },
    });
  }

  private initializeGoogleButton(): void {
    if (!environment.googleClientId) {
      return;
    }

    this.loadGoogleScript().then(() => {
      const googleApi = (window as any).google;
      const button = document.getElementById('google-register-btn');

      if (!googleApi?.accounts?.id || !button) {
        return;
      }

      googleApi.accounts.id.initialize({
        client_id: environment.googleClientId,
        callback: (response: { credential?: string }) => {
          if (response?.credential) {
            this.registerWithGoogle(response.credential);
          }
        },
      });

      button.innerHTML = '';
      googleApi.accounts.id.renderButton(button, {
        theme: 'outline',
        size: 'large',
        width: 320,
        text: 'signup_with',
      });
    });
  }

  private loadGoogleScript(): Promise<void> {
    return new Promise((resolve) => {
      const existing = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
      if (existing) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      document.head.appendChild(script);
    });
  }

  private registerWithGoogle(token: string): void {
    this.loading = true;
    this.error = '';
    this.message = '';
    this.auth.googleLogin(token).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/home']);
      },
      error: () => {
        this.loading = false;
        this.error = 'Google sign-up failed. Please try again.';
      },
    });
  }
}
