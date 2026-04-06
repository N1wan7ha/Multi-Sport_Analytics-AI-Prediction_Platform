import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, catchError, map, of, forkJoin } from 'rxjs';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface Match {
  id: number;
  name: string;
  team1?: Team;
  team2?: Team;
  venue?: Venue;
  format: string;
  category: string;
  status: string;
  match_date: string;
  match_datetime?: string;
  result_text?: string;
  winner?: Team;
  scorecards?: MatchScorecard[];
  live_status_text?: string;
  current_batters?: any[];
  current_bowlers?: any[];
  last_balls?: string;
}

export interface Team {
  id: number;
  name: string;
  short_name?: string;
  logo_url?: string;
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

export interface BatsmanStats {
  batsman?: string;
  runs?: number;
  balls?: number;
  fours?: number;
  sixes?: number;
  strike_rate?: number;
  // Fallbacks for different API formats
  batsmanName?: string;
  name?: string;
  outdec?: string;
  outDesc?: string;
  status?: string;
  r?: number;
  b?: number;
  f4?: number;
  s6?: number;
  '6s'?: number;
  '4s'?: number;
  strikeRate?: number;
  sr?: number;
  strkrate?: number;
  [key: string]: any;
}

export interface BowlerStats {
  bowler?: string;
  overs?: number;
  maidens?: number;
  runs?: number;
  wickets?: number;
  economy?: number;
  // Fallbacks for different API formats
  bowlerName?: string;
  name?: string;
  o?: number;
  m?: number;
  r?: number;
  w?: number;
  eco?: number;
  [key: string]: any;
}

export interface MatchScorecard {
  id: number;
  match: number;
  innings_number?: number;
  batting_team?: Team;
  total_runs?: number;
  total_wickets?: number;
  total_overs?: number;
  run_rate?: number;
  crr?: number;
  rrr?: number;
  batting_data?: BatsmanStats[];
  bowling_data?: BowlerStats[];
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

export interface TeamOption {
  id: number;
  name: string;
  short_name?: string;
  logo_url?: string;
  is_international?: boolean;
}

export interface PlayerOption {
  id: number;
  name: string;
  full_name?: string;
  team_name?: string;
  country?: string;
  image_url?: string;
}

export interface PlayerMatchStats {
  match_id: number;
  match_name: string;
  match_date: string;
  innings_number: number;
  runs_scored?: number;
  balls_faced?: number;
  fours?: number;
  sixes?: number;
  strike_rate?: number;
  overs_bowled?: number;
  runs_conceded?: number;
  wickets_taken?: number;
  economy?: number;
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
  explainability?: Record<string, any>;
  pre_match_projection?: PreMatchProjection;
  current_over?: number | null;
  current_score?: string;
}

export interface ProjectedTeamTotals {
  team_id?: number | null;
  team_name: string;
  projected_score: number;
  projected_score_range: number[];
  projected_wickets_lost: number;
  sample_size: number;
}

export interface ProjectedPerformer {
  player_id: number;
  player_name: string;
  team_id: number;
  team_name: string;
  form_index: number;
  sample_size: number;
}

export interface PreMatchProjection {
  gender_segment?: 'men' | 'women';
  projected_winner?: {
    team_id?: number | null;
    team_name: string;
    win_probability: number;
  };
  team_totals?: {
    team1?: ProjectedTeamTotals;
    team2?: ProjectedTeamTotals;
  };
  top_performers?: {
    top_batter?: ProjectedPerformer | null;
    best_bowler?: ProjectedPerformer | null;
    best_all_rounder?: ProjectedPerformer | null;
  };
  insights?: string[];
}

export interface TeamAnalytics {
  team: string;
  total_matches: number;
  completed_matches: number;
  wins: number;
  losses: number;
  ties_or_no_result: number;
  win_rate_percent: number;
  recent_form?: Array<{ match_id: number; match_name: string; match_date: string; outcome: string }>;
  by_format?: Record<string, number>;
  applied_filters?: {
    format: string;
    category: string;
  };

  // Compatibility fields for legacy consumers
  win_rate: number;
  matches_total: number;
}

export interface PlayerAnalytics {
  player?: { id: number; name: string };
  player_id: number;
  player_name: string;
  matches: number;
  matches_played: number;
  total_runs: number;
  total_wickets: number;
  batting_average?: number;
  avg_runs?: number;
  avg_wickets?: number;
  average_strike_rate?: number;
  average_economy?: number;
  applied_filters?: {
    format: string;
    category: string;
  };
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

export interface CricketNews {
  id: number;
  title: string;
  summary: string;
  content?: string;
  image?: string;
  link: string;
  source: string;
  timestamp?: string;
  category?: 'top' | 'trending' | 'editorial' | 'rankings' | string;
}

export interface InternationalTeam {
  id: number;
  name: string;
  short_name?: string;
  country?: string;
  logo_url?: string;
  total_matches: number;
  wins: number;
  losses: number;
  win_rate: number;
  recent_form?: string;
}

export interface TopPlayer {
  id: number;
  name: string;
  country: string;
  role: string;
  team?: Team;
  total_runs?: number;
  total_wickets?: number;
  matches: number;
}

export interface InternationalStanding {
  rank: number;
  player: string;
  country: string;
  rating: number;
  matches: number;
  format: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  // Matches
  getMatches(
    filters?: {
      status?: string;
      format?: string;
      category?: string;
      search?: string;
      team?: string;
      venue?: string;
      season?: string;
      recommendation?: boolean;
      favoriteTeamIds?: number[];
    },
    page?: number
  ): Observable<{ count: number; results: Match[] }> {
    let params = new HttpParams();
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.format) params = params.set('match_format', filters.format);
    if (filters?.category) params = params.set('match_type', filters.category);
    if (filters?.search) params = params.set('search', filters.search);
    if (filters?.team) params = params.set('team', filters.team);
    if (filters?.venue) params = params.set('venue', filters.venue);
    if (filters?.season) params = params.set('season', filters.season);
    if (filters?.recommendation) params = params.set('recommendation', 'true');
    if (filters?.favoriteTeamIds && filters.favoriteTeamIds.length > 0) {
      params = params.set('favorite_team_ids', filters.favoriteTeamIds.join(','));
    }
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
  getTeamAnalytics(teamName: string, filters?: { format?: string; category?: string }): Observable<TeamAnalytics> {
    let params = new HttpParams();
    if (filters?.format) params = params.set('format', filters.format);
    if (filters?.category) params = params.set('category', filters.category);
    return this.http.get<TeamAnalytics>(`${API_BASE_URL}/analytics/team/${encodeURIComponent(teamName)}/`, { params });
  }

  getPlayerAnalytics(playerId: number, filters?: { format?: string; category?: string }): Observable<PlayerAnalytics> {
    let params = new HttpParams();
    if (filters?.format) params = params.set('format', filters.format);
    if (filters?.category) params = params.set('category', filters.category);
    return this.http.get<PlayerAnalytics>(`${API_BASE_URL}/analytics/player/${playerId}/`, { params });
  }

  // Pipeline Status
  getPipelineStatus(): Observable<PipelineStatus> {
    return this.http.get<PipelineStatus>(`${API_BASE_URL}/pipeline/status/`);
  }

  // User Option Helpers
  getTeamOptions(): Observable<TeamOption[]> {
    return this.http.get<TeamOption[]>(`${API_BASE_URL}/auth/team-options/`);
  }

  getPlayerOptions(query?: string): Observable<PlayerOption[]> {
    const q = (query || '').trim();
    const url = q
      ? `${API_BASE_URL}/auth/player-options/?q=${encodeURIComponent(q)}`
      : `${API_BASE_URL}/auth/player-options/`;
    return this.http.get<PlayerOption[]>(url);
  }

  // New Analytics Endpoints
  getInternationalTeams(): Observable<{ count: number; results: InternationalTeam[] }> {
    return this.http.get<{ count: number; results: InternationalTeam[] }>(`${API_BASE_URL}/analytics/teams/international/`);
  }

  getTopPlayers(metric?: 'runs' | 'wickets' | 'matches', limit?: number): Observable<{ count: number; results: TopPlayer[] }> {
    let params = new HttpParams();
    if (metric) params = params.set('metric', metric);
    if (limit) params = params.set('limit', limit.toString());
    return this.http.get<{ count: number; results: TopPlayer[] }>(`${API_BASE_URL}/analytics/players/top/`, { params });
  }

  getCricketNews(): Observable<{ count: number; results: CricketNews[] }> {
    const feeds = [
      { name: 'ESPNcricinfo', url: 'https://www.espncricinfo.com/rss/content/story/feeds/0.xml' },
      { name: 'Cricbuzz', url: 'https://www.cricbuzz.com/public/rss/live-scores/cricket-news' },
      { name: 'BBC Sport', url: 'https://feeds.bbci.co.uk/sport/cricket/rss.xml' },
      { name: 'The Guardian', url: 'https://www.theguardian.com/sport/cricket/rss' },
      { name: 'Sky Sports', url: 'https://www.skysports.com/rss/12123' },
      { name: 'Sky Sports Cricket', url: 'https://www.skysports.com/rss/12040' },
      { name: 'Wisden', url: 'https://wisden.com/feed' },
      { name: 'BBC Cricket', url: 'https://feeds.bbci.co.uk/sport/cricket/rss.xml' },
      { name: 'ICC News', url: 'https://www.icc-cricket.com/rss/news' },
      { name: 'Hindustan Times', url: 'https://www.hindustantimes.com/rss/cricket/rssfeed.xml' },
      { name: 'NDTV Cricket', url: 'https://feeds.feedburner.com/ndtvsports-cricket' },
      { name: 'News18', url: 'https://www.news18.com/rss/cricket.xml' },
      { name: 'Cricket Times', url: 'https://crickettimes.com/feed/' },
      { name: 'Cricket World', url: 'https://www.cricketworld.com/rss/cricket-news/' },
      { name: 'Al Jazeera', url: 'https://www.aljazeera.com/xml/rss/all.xml' } 
    ];

    const requests = feeds.map(feed => 
      this.http.get<any>(`https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(feed.url)}`).pipe(
        map(response => {
          if (!response || !response.items) return [];
          
          const cricketKeywords = [
            'cricket', 'ipl', 't20', 'odi', 'test', 'match', 'wicket', 'run', 'score', 
            'batsman', 'bowler', 'innings', 'over', 'bcci', 'icc', 'kohli', 'dhoni', 
            'rohit', 'bumrah', 'stokes', 'root', 'cummins', 'smith', 'babar', 'rashid',
            'series', 'tournament', 'world cup', 'toss', 'ash', 'century', 'fifty'
          ];

          return response.items
            .filter((item: any) => {
              const text = ((item.title || '') + (item.description || '') + (item.content || '')).toLowerCase();
              return cricketKeywords.some(kw => text.includes(kw));
            })
            .map((item: any) => {
              let safeImg = item.enclosure?.link || item.thumbnail;
            
            // 1. Precise extraction from description or content
            const htmlToSearch = (item.content || '') + (item.description || '');
            if (!safeImg && htmlToSearch.includes('<img')) {
              // Extract all images and find the first one that doesn't look like a logo/icon
              const allImages = [...htmlToSearch.matchAll(/<img[^>]+src=["']([^"']+)["']/gi)].map(m => m[1]);
              safeImg = allImages.find(src => 
                !src.includes('logo') && 
                !src.includes('icon') && 
                !src.includes('SS-logo') && 
                !src.includes('advert') &&
                !src.endsWith('.gif')
              ) || null;
            }

            // 2. High-Quality Override: Look for explicitly large images if the current one is tiny
            if (safeImg && (safeImg.includes('width=140') || safeImg.includes('240/') || safeImg.includes('150x150'))) {
               // See if there is a more substantial one mentioned in the feed HTML (width >= 600)
               const highResMatch = htmlToSearch.match(/<img[^>]+src=["']([^"']+)["'][^>]+width=["']([6-9]\d{2}|[1-9]\d{3})["']/i);
               if (highResMatch) safeImg = highResMatch[1];
            }

            // Advanced Image Upscaling logic for multiple sources
            if (safeImg) {
              // 1. ESPN High-Resolution Upscale
              if (safeImg.includes('p.imgci.com/db/PICTURES')) {
                safeImg = safeImg.replace(/\.\d+\.jpg$/, '.jpg');
                if (!safeImg.includes('img1.hscicdn.com')) {
                   safeImg = safeImg.replace(/https?:\/\/p\.imgci\.com\/db\/PICTURES/, 'https://img1.hscicdn.com/image/upload/f_auto,t_ds_wide_w_1280,q_80/lsci/db/PICTURES');
                }
              }
              // 2. Cricbuzz Professional Quality Upscale
              else if (safeImg.includes('static.cricbuzz.com')) {
                safeImg = safeImg.replace(/\/\d+x\d+\//, '/1200x675/');
              }
              // 3. BBC Sport HD Upscale
              else if (safeImg.includes('ichef.bbci.co.uk')) {
                // Use 800px instead of 1024px as it is more universally supported
                safeImg = safeImg.replace(/\/(100|150|240|320|480|640)\//, '/800/');
              }
              // 4. Sky Sports, The Guardian & News Outlets Upscale
              else if (safeImg.includes('ndtvimg.com') || safeImg.includes('news18.com') || safeImg.includes('wisden.com')) {
                // Safe to upscale ndtv, news18 and Wisden
                safeImg = safeImg.replace(/(\d+)[x_](\d+)/, '1024x576');
              }
              // Skip upscaling for The Guardian (guim.co.uk), Sky Sports, and BBC as they use signed or sensitive URLs
              // 5. Generalized Upscale for unknown sources (Unsplash, etc.)
              else {
                const resMatch = safeImg.match(/\/(\d+)[x_](\d+)\//);
                if (resMatch) {
                   const width = parseInt(resMatch[1], 10);
                   if (width < 600) {
                     safeImg = safeImg.replace(resMatch[0], '/1200x675/');
                   }
                }
              }
            }




            return {
              id: Math.floor(Math.random() * 1000000),
              title: item.title,
              summary: item.description?.replace(/<[^>]*>?/gm, '').slice(0, 180) + '...',
              content: item.content || item.description,
              link: item.link,
              source: feed.name,
              image: safeImg || null,
              category: 'Live Coverage',
              timestamp: new Date(item.pubDate || Date.now()).getTime().toString()
            } as CricketNews;
          });
        }),
        catchError(() => of([]))
      )
    );

    return forkJoin(requests).pipe(
      map(results => {
        const flattened = results.flat();
        // Sort by time (newest first)
        flattened.sort((a, b) => Number(b.timestamp) - Number(a.timestamp));
        // Unique by title
        const unique = flattened.filter((v, i, a) => a.findIndex(t => t.title === v.title) === i);
        // Only keep mostly cricket news for general feeds
        const filtered = unique.filter(item => 
          item.source !== 'Al Jazeera' || 
          item.title.toLowerCase().includes('cricket') || 
          item.title.toLowerCase().includes('ipl') ||
          item.title.toLowerCase().includes('world cup')
        );
        return { count: filtered.length, results: filtered };
      }),
      catchError(() => {
        return this.http.get<{ count: number; results: CricketNews[] }>(`${API_BASE_URL}/analytics/news/`);
      })
    );
  }

  getInternationalStandings(format?: 'test' | 'odi' | 't20'): Observable<{ count: number; format: string; results: InternationalStanding[] }> {
    let params = new HttpParams();
    if (format) params = params.set('format', format);
    return this.http.get<{ count: number; format: string; results: InternationalStanding[] }>(`${API_BASE_URL}/analytics/standings/international/`, { params });
  }

  triggerMatchSync(matchId: number): Observable<any> {
    return this.http.post(`${API_BASE_URL}/pipeline/sync-match/`, { match_id: matchId });
  }
}
