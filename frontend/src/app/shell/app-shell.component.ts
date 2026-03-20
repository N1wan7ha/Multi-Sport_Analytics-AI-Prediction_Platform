import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../core/services/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-shell">
      <aside class="sidebar" [class.sidebar-open]="mobileNavOpen()">
        <div class="brand-row">
          <div>
            <p class="brand-kicker">Prediction Platform</p>
            <h2>MatchMind</h2>
          </div>
          <button class="mobile-close" (click)="toggleMobileNav()">✕</button>
        </div>

        <nav class="nav-list">
          <a routerLink="/dashboard" routerLinkActive="active-link">Dashboard</a>
          <a routerLink="/matches" routerLinkActive="active-link">Matches</a>
          <a routerLink="/series" routerLinkActive="active-link">Series</a>
          <a routerLink="/players" routerLinkActive="active-link">Players</a>
          <a routerLink="/analytics" routerLinkActive="active-link">Analytics</a>
          <a routerLink="/auth/profile" routerLinkActive="active-link">Profile</a>
          <a *ngIf="isAdmin()" routerLink="/admin/users" routerLinkActive="active-link">Admin</a>
        </nav>
      </aside>

      <div class="sidebar-backdrop" *ngIf="mobileNavOpen()" (click)="toggleMobileNav()"></div>

      <main class="main-content" style="margin-left: var(--sidebar-width); padding-top: var(--topbar-height);">
        <header class="topbar">
          <button class="menu-btn" (click)="toggleMobileNav()">☰</button>
          <div class="topbar-title-wrap">
            <h3 class="topbar-title">Control Center</h3>
            <p class="topbar-subtitle">Live operations and prediction workflow</p>
          </div>
          <div class="topbar-right">
            <span class="state-pill">Realtime</span>
            <span class="user-role" *ngIf="isAdmin()">Admin</span>
            <button class="btn btn-secondary" (click)="logout()">Logout</button>
          </div>
        </header>

        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    .sidebar {
      width: var(--sidebar-width);
      background: linear-gradient(180deg, #0f1623 0%, #101c31 100%);
      border-right: 1px solid var(--border-subtle);
      position: fixed;
      inset: 0 auto 0 0;
      z-index: 35;
      padding: 1.1rem;
      transform: translateX(0);
      transition: transform 0.25s ease;
    }

    .brand-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.2rem;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 1rem;
    }

    .brand-kicker {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      font-size: 0.68rem;
      line-height: 1;
      margin-bottom: 0.3rem;
    }

    .brand-row h2 {
      margin: 0;
      font-size: 1.55rem;
    }

    .mobile-close {
      display: none;
      border: none;
      background: transparent;
      color: var(--text-primary);
      font-size: 1rem;
      cursor: pointer;
    }

    .nav-list {
      display: grid;
      gap: 0.52rem;
    }

    .nav-list a {
      padding: 0.68rem 0.82rem;
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      border: 1px solid transparent;
      font-weight: 500;
      letter-spacing: 0.01em;
    }

    .nav-list a:hover,
    .nav-list a.active-link {
      color: var(--text-primary);
      background: var(--bg-card);
      border-color: var(--border-muted);
      transform: translateX(2px);
    }

    .topbar {
      height: var(--topbar-height);
      position: fixed;
      left: var(--sidebar-width);
      right: 0;
      top: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1rem;
      border-bottom: 1px solid var(--border-subtle);
      background: rgba(8, 12, 20, 0.86);
      backdrop-filter: blur(8px);
      z-index: 30;
    }

    .topbar-title-wrap {
      display: grid;
      gap: 0.1rem;
      margin-left: 0.5rem;
    }

    .topbar-title {
      font-size: 1.05rem;
      line-height: 1.1;
      margin: 0;
    }

    .topbar-subtitle {
      color: var(--text-muted);
      font-size: 0.74rem;
      margin: 0;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .state-pill {
      font-size: 0.72rem;
      color: var(--color-primary);
      border: 1px solid var(--border-primary);
      background: var(--color-primary-muted);
      padding: 0.22rem 0.5rem;
      border-radius: var(--radius-full);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
    }

    .user-role {
      font-size: 0.8rem;
      color: var(--color-accent);
      border: 1px solid var(--color-accent-muted);
      padding: 0.2rem 0.45rem;
      border-radius: var(--radius-full);
    }

    .menu-btn {
      display: none;
      border: none;
      background: transparent;
      color: var(--text-primary);
      font-size: 1.1rem;
      cursor: pointer;
    }

    .sidebar-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.55);
      z-index: 20;
    }

    @media (max-width: 1024px) {
      .sidebar {
        transform: translateX(-100%);
      }

      .sidebar.sidebar-open {
        transform: translateX(0);
      }

      .mobile-close,
      .menu-btn,
      .sidebar-backdrop {
        display: block;
      }

      .topbar {
        left: 0;
      }

      .topbar-title-wrap,
      .state-pill {
        display: none;
      }

      .main-content {
        margin-left: 0 !important;
      }
    }
  `],
})
export class AppShellComponent {
  mobileNavOpen = signal(false);
  isAdmin = computed(() => this.authService.getCurrentUserRole() === 'ADMIN');

  constructor(private authService: AuthService, private router: Router) {}

  toggleMobileNav(): void {
    this.mobileNavOpen.update((v) => !v);
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/auth/login']);
  }
}
