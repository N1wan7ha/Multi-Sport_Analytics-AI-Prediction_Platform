/**
 * Core domain models — MatchMind (Multi-Sport Prediction Platform)
 */

export interface Team {
    id: number;
    name: string;
    short_name: string;
    country: string;
    is_international: boolean;
}

export interface Venue {
    id: number;
    name: string;
    city: string;
    country: string;
    pitch_type: 'batting' | 'bowling' | 'balanced';
}

export interface Match {
    id: number;
    name: string;
    cricapi_id: string;
    cricbuzz_id: string;
    team1: Team;
    team2: Team;
    venue: Venue | null;
    format: 'test' | 'odi' | 't20' | 't10' | 'other';
    category: 'international' | 'franchise' | 'domestic';
    status: 'upcoming' | 'live' | 'complete' | 'abandoned';
    match_date: string;
    result_text: string;
    scorecards: Scorecard[];
    created_at: string;
    updated_at: string;
}

export interface Scorecard {
    innings_number: number;
    batting_team: Team;
    total_runs: number;
    total_wickets: number;
    total_overs: number;
    run_rate: number;
    batting_data: any[];
    bowling_data: any[];
}

export interface Player {
    id: number;
    cricapi_id: string;
    name: string;
    full_name: string;
    country: string;
    batting_style: string;
    bowling_style: string;
    role: 'batsman' | 'bowler' | 'all_rounder' | 'wicket_keeper';
    image_url: string;
}

export interface Series {
    id: number;
    cricapi_id: string;
    name: string;
    start_date: string;
    end_date: string;
    odi_matches_count: number;
    t20_matches_count: number;
    test_matches_count: number;
}

export interface PredictionJob {
    id: number;
    match: number;
    prediction_type: 'pre_match' | 'live';
    status: 'pending' | 'processing' | 'complete' | 'failed';
    model_version: string;
    requested_at: string;
    completed_at: string | null;
}

export interface PredictionResult {
    job: PredictionJob;
    team1: Team;
    team2: Team;
    team1_win_probability: number;
    team2_win_probability: number;
    draw_probability: number;
    confidence_score: number;
    key_factors: KeyFactor[];
}

export interface KeyFactor {
    factor: string;
    impact: number;         // -1 to 1
    direction: 'positive' | 'negative' | 'neutral';
}

export interface DashboardStats {
    total_matches: number;
    live_matches: number;
    upcoming_matches: number;
    total_players: number;
}

export interface ApiResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

export interface AuthTokens {
    access: string;
    refresh: string;
}

export interface User {
    id: number;
    email: string;
    username: string;
    role: 'ADMIN' | 'USER';
    email_verified?: boolean;
    favourite_team: string;
    bio?: string;
    favourite_team_ids?: number[];
    favourite_teams?: Array<{
        id: number;
        name: string;
        short_name?: string;
    }>;
}

export interface AdminUser {
    id: number;
    email: string;
    username: string;
    role: 'ADMIN' | 'USER';
    is_active: boolean;
    date_joined: string;
    last_login: string | null;
}

export interface ActivitySummary {
    new_registrations_7d: number;
    new_registrations_30d: number;
    prediction_requests_total: number;
    pre_match: number;
    live: number;
    active_users_7d: number;
    syncs_24h: number;
}
