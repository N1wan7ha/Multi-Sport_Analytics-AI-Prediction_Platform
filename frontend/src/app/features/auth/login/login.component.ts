import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <div class="card">
        <h1>Login</h1>
        <p class="text-secondary" style="margin-top:0.5rem">Authenticate to create prediction jobs.</p>

        <div style="margin-top:1rem; display:grid; gap:.75rem; max-width:420px;">
          <input class="input" type="email" [(ngModel)]="email" placeholder="Email" />
          <input class="input" type="password" [(ngModel)]="password" placeholder="Password" />
          <button class="btn btn-primary" (click)="login()" [disabled]="loading">
            {{ loading ? 'Signing in...' : 'Sign in' }}
          </button>
          <p *ngIf="error" style="color:#d83a52;">{{ error }}</p>
        </div>
      </div>
    </div>
  `,
})
export class LoginComponent {
  email = '';
  password = '';
  loading = false;
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  login(): void {
    if (!this.email || !this.password) return;
    this.loading = true;
    this.error = '';
    this.auth.login(this.email, this.password).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.loading = false;
        this.error = 'Login failed. Check your credentials.';
      },
    });
  }
}
