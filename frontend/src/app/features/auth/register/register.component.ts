import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

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
          <p *ngIf="message" class="text-secondary">{{ message }}</p>
          <p *ngIf="error" style="color:#d83a52;">{{ error }}</p>
        </div>
      </div>
    </div>
  `,
})
export class RegisterComponent {
  email = '';
  username = '';
  password = '';
  loading = false;
  message = '';
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  register(): void {
    if (!this.email || !this.username || !this.password) return;
    this.loading = true;
    this.message = '';
    this.error = '';

    this.auth.register(this.email, this.username, this.password).subscribe({
      next: () => {
        this.loading = false;
        this.message = 'Account created. Please login.';
        setTimeout(() => this.router.navigate(['/auth/login']), 700);
      },
      error: () => {
        this.loading = false;
        this.error = 'Registration failed. Try a different email/username.';
      },
    });
  }
}
