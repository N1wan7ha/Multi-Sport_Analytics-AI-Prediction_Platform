import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },

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
  { path: '**', redirectTo: 'dashboard' },
];
