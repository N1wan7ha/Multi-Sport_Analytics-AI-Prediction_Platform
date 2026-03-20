import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },

  {
    path: 'auth/login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(m => m.LoginComponent),
    title: 'Login — MatchMind',
  },
  {
    path: 'auth/register',
    loadComponent: () =>
      import('./features/auth/register/register.component').then(m => m.RegisterComponent),
    title: 'Register — MatchMind',
  },
  {
    path: 'auth/verify-email',
    loadComponent: () =>
      import('./features/auth/verify-email/verify-email.component').then(m => m.VerifyEmailComponent),
    title: 'Verify Email — MatchMind',
  },

  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./shell/app-shell.component').then(m => m.AppShellComponent),
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
        title: 'Dashboard — MatchMind',
      },
      {
        path: 'matches',
        loadComponent: () =>
          import('./features/matches/match-list/match-list.component').then(m => m.MatchListComponent),
        title: 'Matches — MatchMind',
      },
      {
        path: 'matches/:id',
        loadComponent: () =>
          import('./features/matches/match-detail/match-detail.component').then(m => m.MatchDetailComponent),
        title: 'Match Detail — MatchMind',
      },
      {
        path: 'matches/:id/predict',
        loadComponent: () =>
          import('./features/predictions/prediction-view/prediction-view.component').then(m => m.PredictionViewComponent),
        title: 'Prediction — MatchMind',
      },
      {
        path: 'series',
        loadComponent: () =>
          import('./features/series/series-list/series-list.component').then(m => m.SeriesListComponent),
        title: 'Series — MatchMind',
      },
      {
        path: 'series/:id',
        loadComponent: () =>
          import('./features/series/series-detail/series-detail.component').then(m => m.SeriesDetailComponent),
        title: 'Series Detail — MatchMind',
      },
      {
        path: 'players',
        loadComponent: () =>
          import('./features/players/player-list/player-list.component').then(m => m.PlayerListComponent),
        title: 'Players — MatchMind',
      },
      {
        path: 'players/:id',
        loadComponent: () =>
          import('./features/players/player-detail/player-detail.component').then(m => m.PlayerDetailComponent),
        title: 'Player Profile — MatchMind',
      },
      {
        path: 'analytics',
        loadComponent: () =>
          import('./features/analytics/analytics-dashboard/analytics-dashboard.component').then(m => m.AnalyticsDashboardComponent),
        title: 'Analytics — MatchMind',
      },
      {
        path: 'auth/profile',
        loadComponent: () =>
          import('./features/auth/profile/profile.component').then(m => m.ProfileComponent),
        title: 'Profile — MatchMind',
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/admin/admin.component').then(m => m.AdminDashboardComponent),
        children: [
          {
            path: 'users',
            loadComponent: () =>
              import('./features/admin/components/admin-users.component').then(m => m.AdminUsersComponent),
          },
          {
            path: 'activity',
            loadComponent: () =>
              import('./features/admin/components/admin-activity.component').then(m => m.AdminActivityComponent),
          },
          {
            path: 'pipeline',
            loadComponent: () =>
              import('./features/admin/components/admin-pipeline.component').then(m => m.AdminPipelineComponent),
          },
          {
            path: 'metrics',
            loadComponent: () =>
              import('./features/admin/components/admin-metrics.component').then(m => m.AdminMetricsComponent),
          },
          {
            path: 'predictions',
            loadComponent: () =>
              import('./features/admin/components/admin-predictions.component').then(m => m.AdminPredictionsComponent),
          },
          { path: '', redirectTo: 'users', pathMatch: 'full' },
        ],
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },

  { path: '**', redirectTo: 'dashboard' },
];
