import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { filter, catchError } from 'rxjs/operators';
import { of } from 'rxjs';

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
          <a routerLink="/home" routerLinkActive="active-link">Home</a>
          <a routerLink="/matches" routerLinkActive="active-link">Matches</a>
          <a routerLink="/series" routerLinkActive="active-link">Series</a>
          <a routerLink="/players" routerLinkActive="active-link">Players</a>
          <a routerLink="/analytics" routerLinkActive="active-link">Analytics</a>

          <!-- Premium/Login-Required Routes -->
          <div *ngIf="isLoggedIn()" style="border-top: 1px solid var(--border-subtle); margin-top: 0.75rem; padding-top: 0.75rem;">
            <a routerLink="/predictions" routerLinkActive="active-link">Predictions</a>
            <a routerLink="/favorites" routerLinkActive="active-link">Favorites</a>
            <a routerLink="/history" routerLinkActive="active-link">History</a>
            <a routerLink="/auth/profile" routerLinkActive="active-link">Profile</a>
          </div>

          <!-- Guest Login Link -->
          <a *ngIf="!isLoggedIn()" class="nav-login-link" style="color: var(--text-accent); font-weight: 500; margin-top: 0.75rem; border-top: 1px solid var(--border-subtle); padding-top: 0.75rem;" routerLink="/auth/login">→ Login for Premium</a>

          <a *ngIf="isAdmin()" routerLink="/admin/overview" routerLinkActive="active-link">Admin</a>
        </nav>
      </aside>

      <div class="sidebar-backdrop" *ngIf="mobileNavOpen()" (click)="toggleMobileNav()"></div>

      <main class="main-content" style="margin-left: var(--sidebar-width); padding-top: var(--topbar-height);">
        <header class="topbar">
          <button class="menu-btn" (click)="toggleMobileNav()">☰</button>
          <div class="topbar-title-wrap">
            <h3 class="topbar-title">{{ pageTitle() }}</h3>
            <p class="topbar-subtitle">{{ pageSubtitle() }}</p>
          </div>
          <div class="topbar-right">
            <span class="state-pill">Realtime</span>
            <span class="user-role" *ngIf="isAdmin()">Admin</span>
            <a *ngIf="!isLoggedIn()" class="btn btn-primary" routerLink="/auth/login">Login</a>
            <button *ngIf="isLoggedIn()" class="btn btn-secondary" (click)="logout()">Logout</button>
          </div>
        </header>

        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    .sidebar {
      width: var(--sidebar-width);
      background:
        radial-gradient(circle at 8% 12%, rgba(34, 211, 238, 0.13), transparent 32%),
        linear-gradient(180deg, #0f1623 0%, #101c31 100%);
      border-right: 1px solid var(--border-subtle);
      position: fixed;
      inset: 0 auto 0 0;
      z-index: 35;
      padding: 1.1rem;
      transform: translateX(0);
      transition: transform 0.25s ease;
      box-shadow: 10px 0 28px rgba(0, 0, 0, 0.22);
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
      background: linear-gradient(90deg, #e2e8f0 0%, #67e8f9 100%);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
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
      position: relative;
      padding: 0.68rem 0.82rem 0.68rem 1.2rem;
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      border: 1px solid transparent;
      font-weight: 500;
      letter-spacing: 0.01em;
      transition: all 0.2s ease;
      overflow: hidden;
    }

    .nav-list a:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.04);
      transform: translateX(2px);
    }

    .nav-list a.active-link {
      color: #fff;
      background: linear-gradient(90deg, rgba(0, 212, 170, 0.15) 0%, rgba(6, 182, 212, 0.05) 100%);
      border-color: rgba(0, 212, 170, 0.4);
      box-shadow: 0 4px 12px rgba(0, 212, 170, 0.15);
      transform: translateX(4px);
    }

    .nav-list a.active-link::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: #00d4aa;
      box-shadow: 0 0 10px #00d4aa;
      border-radius: 4px 0 0 4px;
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
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      background: linear-gradient(90deg, rgba(8, 12, 20, 0.65), rgba(10, 22, 38, 0.75));
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      box-shadow: 0 4px 24px rgba(0,0,0,0.1);
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
      background: linear-gradient(90deg, rgba(34, 197, 94, 0.15), rgba(6, 182, 212, 0.2));
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
  pageTitle = signal('Home Center');
  pageSubtitle = signal('Matches, analytics, favorites and AI predictions');
  mobileNavOpen = signal(false);
  
  isLoggedIn = computed(() => this.authService.isLoggedIn());
  isAdmin = computed(() => this.authService.getCurrentUserRole() === 'ADMIN');

  constructor(private authService: AuthService, private router: Router) {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).pipe(
      catchError(() => of(null))
    ).subscribe(() => {
      this.updateTitles();
    });
    this.updateTitles(); // Initial call
  }

  private updateTitles(): void {
    const url = this.router.url;
    if (url.includes('/home')) {
      this.pageTitle.set('Home Center');
      this.pageSubtitle.set('Matches, analytics, favorites and AI predictions');
    } else if (url.includes('/matches')) {
      this.pageTitle.set('Intelligence Hub');
      this.pageSubtitle.set('Global Match Stream & Neural Predictions');
    } else if (url.includes('/series')) {
      this.pageTitle.set('Series Archive');
      this.pageSubtitle.set('Global Cricket Tournaments & Leagues');
    } else if (url.includes('/players')) {
      this.pageTitle.set('Player Bio-Data');
      this.pageSubtitle.set('Global Talent Scouting & Performance Metrics');
    } else if (url.includes('/analytics')) {
      this.pageTitle.set('Neural Analytics');
      this.pageSubtitle.set('Deep Learning Insights & Probability Models');
    } else if (url.includes('/predictions')) {
      this.pageTitle.set('AI Prediction Center');
      this.pageSubtitle.set('High-Fidelity Match Outcomes');
    }
  }

  toggleMobileNav(): void {
    this.mobileNavOpen.update((v) => !v);
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/auth/login']);
  }
}
