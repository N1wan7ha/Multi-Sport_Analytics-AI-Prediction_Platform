import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },

  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
    title: 'Dashboard — Cricket Analytics',
  },
  {
    path: 'matches',
    loadComponent: () =>
      import('./features/matches/match-list/match-list.component').then(m => m.MatchListComponent),
    title: 'Matches — Cricket Analytics',
  },
  {
    path: 'matches/:id',
    loadComponent: () =>
      import('./features/matches/match-detail/match-detail.component').then(m => m.MatchDetailComponent),
    title: 'Match Detail — Cricket Analytics',
  },
  {
    path: 'matches/:id/predict',
    loadComponent: () =>
      import('./features/predictions/prediction-view/prediction-view.component').then(m => m.PredictionViewComponent),
    title: 'Prediction — Cricket Analytics',
  },
  {
    path: 'series',
    loadComponent: () =>
      import('./features/series/series-list/series-list.component').then(m => m.SeriesListComponent),
    title: 'Series — Cricket Analytics',
  },
  {
    path: 'players',
    loadComponent: () =>
      import('./features/players/player-list/player-list.component').then(m => m.PlayerListComponent),
    title: 'Players — Cricket Analytics',
  },
  {
    path: 'players/:id',
    loadComponent: () =>
      import('./features/players/player-detail/player-detail.component').then(m => m.PlayerDetailComponent),
    title: 'Player Profile — Cricket Analytics',
  },
  {
    path: 'analytics',
    loadComponent: () =>
      import('./features/analytics/analytics-dashboard/analytics-dashboard.component').then(m => m.AnalyticsDashboardComponent),
    title: 'Analytics — Cricket Analytics',
  },
  {
    path: 'auth/login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(m => m.LoginComponent),
    title: 'Login — Cricket Analytics',
  },
  {
    path: 'auth/register',
    loadComponent: () =>
      import('./features/auth/register/register.component').then(m => m.RegisterComponent),
    title: 'Register — Cricket Analytics',
  },
  { path: '**', redirectTo: 'dashboard' },
];
