import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface Match {
  id: number;
  name: string;
  team1: Team;
  team2: Team;
  venue?: Venue;
  format: string;
  category: string;
  status: string;
  match_date: string;
  match_datetime?: string;
  winner?: Team;
  scorecards?: MatchScorecard[];
}

export interface Team {
  id: number;
  name: string;
  short_name?: string;
  is_international?: boolean;
}

export interface Venue {
  id: number;
  name: string;
  city: string;
  country: string;
  pitch_type: string;
  avg_first_innings_score?: number;
}

export interface MatchScorecard {
  id: number;
  match: number;
  team: Team;
  runs: number;
  wickets: number;
}

export interface Player {
  id: number;
  name: string;
  full_name: string;
  country: string;
  team?: Team;
  role: string;
  recent_stats?: PlayerMatchStats[];
}

export interface PlayerMatchStats {
  id: number;
  player: number;
  match: number;
  runs: number;
  wickets: number;
  match_date: string;
}

export interface Series {
  id: number;
  name: string;
  year: number;
  raw_data?: any;
  matches?: Match[];
}

export interface PredictionJob {
  id: number;
  match: number;
  match_detail?: Match;
  requested_by: number;
  prediction_type: string;
  status: string;
  model_version: string;
  result?: PredictionResult;
  created_at: string;
  completed_at?: string;
}

export interface PredictionResult {
  id: number;
  job: number;
  team1: Team;
  team2: Team;
  team1_win_probability: number;
  team2_win_probability: number;
  draw_probability?: number;
  confidence_score: number;
  key_factors: Record<string, any>;
  feature_snapshot: Record<string, any>;
  model_kind?: string;
  current_over?: number | null;
  current_score?: string;
}

export interface TeamAnalytics {
  team: Team;
  win_rate: number;
  losses: number;
  matches_total: number;
  recent_form?: string;
  by_format?: Record<string, any>;
}

export interface PlayerAnalytics {
  player: Player;
  matches_played: number;
  total_runs: number;
  total_wickets: number;
  avg_runs?: number;
  avg_wickets?: number;
}

export interface PipelineStatus {
  last_sync_current_matches: string;
  count_current_matches: number;
  last_sync_cricbuzz_live: string;
  count_cricbuzz_live: number;
  last_sync_completed_matches: string;
  count_completed_matches: number;
  last_sync_player_stats: string;
  count_player_stats: number;
  last_sync_unified_matches: string;
  count_unified_matches: number;
  last_model_retraining: string;
  model_retraining_status: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  // Matches
  getMatches(filters?: { status?: string; format?: string; category?: string; search?: string }, page?: number): Observable<{ count: number; results: Match[] }> {
    let params = new HttpParams();
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.format) params = params.set('format', filters.format);
    if (filters?.category) params = params.set('category', filters.category);
    if (filters?.search) params = params.set('search', filters.search);
    if (page) params = params.set('page', page);
    return this.http.get<{ count: number; results: Match[] }>(`${API_BASE_URL}/matches/`, { params });
  }

  getMatch(id: number): Observable<Match> {
    return this.http.get<Match>(`${API_BASE_URL}/matches/${id}/`);
  }

  getLiveMatches(): Observable<{ count: number; results: Match[] }> {
    return this.http.get<{ count: number; results: Match[] }>(`${API_BASE_URL}/matches/live/`);
  }

  // Players
  getPlayers(filters?: { search?: string }, page?: number): Observable<{ count: number; results: Player[] }> {
    let params = new HttpParams();
    if (filters?.search) params = params.set('search', filters.search);
    if (page) params = params.set('page', page);
    return this.http.get<{ count: number; results: Player[] }>(`${API_BASE_URL}/players/`, { params });
  }

  getPlayer(id: number): Observable<Player> {
    return this.http.get<Player>(`${API_BASE_URL}/players/${id}/`);
  }

  // Series
  getSeries(page?: number): Observable<{ count: number; results: Series[] }> {
    let params = new HttpParams();
    if (page) params = params.set('page', page);
    return this.http.get<{ count: number; results: Series[] }>(`${API_BASE_URL}/series/`, { params });
  }

  getSeriesMatches(seriesId: number, page?: number): Observable<{ count: number; results: Match[] }> {
    let params = new HttpParams();
    if (page) params = params.set('page', page);
    return this.http.get<{ count: number; results: Match[] }>(`${API_BASE_URL}/series/${seriesId}/matches/`, { params });
  }

  // Predictions
  createPrediction(
    matchId: number,
    predictionType: string,
    liveContext?: { current_over: number; current_score?: string }
  ): Observable<PredictionJob> {
    return this.http.post<PredictionJob>(`${API_BASE_URL}/predictions/`, {
      match: matchId,
      prediction_type: predictionType,
      ...(liveContext ?? {}),
    });
  }

  getPrediction(id: number): Observable<PredictionJob> {
    return this.http.get<PredictionJob>(`${API_BASE_URL}/predictions/${id}/`);
  }

  getLatestPredictionForMatch(matchId: number, predictionType?: 'pre_match' | 'live'): Observable<PredictionJob> {
    let params = new HttpParams();
    if (predictionType) params = params.set('prediction_type', predictionType);
    return this.http.get<PredictionJob>(`${API_BASE_URL}/predictions/match/${matchId}/`, { params });
  }

  // Analytics
  getTeamAnalytics(teamName: string): Observable<TeamAnalytics> {
    return this.http.get<TeamAnalytics>(`${API_BASE_URL}/analytics/team/${encodeURIComponent(teamName)}/`);
  }

  getPlayerAnalytics(playerId: number): Observable<PlayerAnalytics> {
    return this.http.get<PlayerAnalytics>(`${API_BASE_URL}/analytics/player/${playerId}/`);
  }

  // Pipeline Status
  getPipelineStatus(): Observable<PipelineStatus> {
    return this.http.get<PipelineStatus>(`${API_BASE_URL}/pipeline/status/`);
  }
}
