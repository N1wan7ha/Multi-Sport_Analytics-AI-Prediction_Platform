import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Match, PredictionJob, CricketNews, InternationalStanding, TopPlayer } from '../../../core/services/api.service';
import { LivePredictionSocketService } from '../../../core/services/live-prediction-socket.service';
import { AuthService } from '../../../core/services/auth.service';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Component({
  selector: 'app-match-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up matches-intelligence">
      
      <!-- Premium Hero Banner -->
      <section class="card intelligence-hero">
        <div class="hero-content">
          <div class="hero-badge">
             <div class="pulse-dot"></div>
             <span>Multi-Source Intelligence Core</span>
          </div>
          <h1>Matches Control Board</h1>
          <p class="text-secondary">
            Synthesized insights from 8+ trusted global feeds. 
            <span *ngIf="!isLoggedIn" class="login-hint">Login to unlock neural predictions.</span>
          </p>

          <div class="hero-stats-ribbon">
            <div class="stat-pill" (click)="setTab('')" [class.active]="activeTab === ''">
              <label>Monitoring</label>
              <strong>{{ matches.length }} Matches</strong>
            </div>
            <div class="stat-pill live" (click)="setTab('live')" [class.active]="activeTab === 'live'">
              <div class="live-indicator" *ngIf="liveVisibleCount > 0"></div>
              <label>Live Now</label>
              <strong>{{ liveVisibleCount }}</strong>
            </div>
            <div class="stat-pill upcoming" (click)="setTab('upcoming')" [class.active]="activeTab === 'upcoming'">
              <label>Upcoming</label>
              <strong>{{ upcomingVisibleCount }}</strong>
            </div>
            <div class="stat-pill complete" (click)="setTab('complete')" [class.active]="activeTab === 'complete'">
              <label>Completed</label>
              <strong>{{ completedVisibleCount }}</strong>
            </div>
          </div>
        </div>

        <div class="hero-filters">
           <div class="filter-group">
             <span class="filter-label" style="font-size: 0.65rem; font-weight: 800; color: var(--color-primary);">FORMAT</span>
             <select [(ngModel)]="format" (change)="load()" class="dashboard-select">
               <option value="">All Disciplines</option>
               <option value="test">Test Cricket</option>
               <option value="odi">One Day International</option>
               <option value="t20">T20 Global League</option>
             </select>
           </div>
           <div class="filter-group search-box">
             <input type="text" [(ngModel)]="searchQuery" (keyup.enter)="load()" placeholder="Search teams or venues..." class="dashboard-input">
             <button (click)="load()" class="search-btn">
               <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
             </button>
           </div>
        </div>
      </section>

      <div class="intelligence-layout">
        <!-- Main Match Feed -->
        <main class="match-stream">
          <div class="section-tabs">
            <button class="tab-btn" [class.active]="activeTab === ''" (click)="setTab('')">ALL FEED</button>
            <button class="tab-btn" [class.active]="activeTab === 'live'" (click)="setTab('live')">
              LIVE <span class="count-badge" *ngIf="liveVisibleCount > 0">{{ liveVisibleCount }}</span>
            </button>
            <button class="tab-btn" [class.active]="activeTab === 'upcoming'" (click)="setTab('upcoming')">UPCOMING</button>
            <button class="tab-btn" [class.active]="activeTab === 'complete'" (click)="setTab('complete')">COMPLETED</button>
            
            <div class="tab-spacer"></div>
            
            <div class="refresh-indicator" [class.visible]="loading">
               <div class="spinner"></div>
               <span>Syncing Feeds...</span>
            </div>
          </div>

          <div class="match-grid">
            <div *ngIf="error" class="card error-card">
              <p>{{ error }}</p>
              <button (click)="load()" class="btn btn-secondary">Retry Connection</button>
            </div>

            <div *ngFor="let match of matches" class="match-intel-card" [class.live-pulse]="match.status === 'live'">
              <a [routerLink]="['/matches', match.id]" class="card-link">
                <div class="card-header">
                  <div class="match-tags">
                    <span class="badge badge--{{ match.status === 'live' ? 'live' : (match.status === 'complete' ? 'complete' : 'upcoming') }}">
                      <span class="dot" *ngIf="match.status === 'live'"></span>
                      {{ match.status | uppercase }}
                    </span>
                    <span class="format-tag">{{ match.format === 'other' ? 'GLOBAL LEAGUE' : (match.format | uppercase) }}</span>
                  </div>
                  <span class="match-time" *ngIf="match.status === 'upcoming'">{{ match.match_date | date:'MMM d, y' }}</span>
                  <span class="match-time" *ngIf="match.status === 'complete'">Archive Node</span>
                </div>

                <div class="teams-arena">
                  <div class="team-side">
                    <div class="logo-wrap">
                      <img [src]="match.team1?.logo_url || 'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?w=100'" [alt]="match.team1?.name">
                    </div>
                    <strong>{{ match.team1?.name || 'Unknown' }}</strong>
                  </div>
                  <div class="vs-divider">
                    <div class="vs-text">VS</div>
                    <div class="vs-line"></div>
                  </div>
                  <div class="team-side">
                     <div class="logo-wrap">
                      <img [src]="match.team2?.logo_url || 'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?w=100'" [alt]="match.team2?.name">
                    </div>
                    <strong>{{ match.team2?.name || 'Unknown' }}</strong>
                  </div>
                </div>

                <!-- Live Scoreboard Preview (If available) -->
                <div class="score-preview" *ngIf="match.status === 'live' || match.status === 'complete'">
                   <div *ngIf="match.scorecards && match.scorecards.length > 0; else noScore" class="score-display">
                      <div class="score-row" *ngFor="let sc of match.scorecards; let i = index">
                        <span class="team-name">{{ sc.batting_team?.name || 'Innings ' + sc.innings_number }}</span>
                        <div class="score-val">
                          <strong>{{ sc.total_runs }}/{{ sc.total_wickets }}</strong>
                          <span class="overs">({{ sc.total_overs }} ov)</span>
                          <span class="crr-tag" *ngIf="match.status === 'live' && sc.crr">CRR {{ sc.crr }}</span>
                        </div>
                      </div>
                      <div class="live-commentary" *ngIf="match.status === 'live' && match.live_status_text">
                         {{ match.live_status_text }}
                      </div>
                   </div>
                   <ng-template #noScore>
                      <div class="score-text" *ngIf="match.result_text">{{ match.result_text }}</div>
                      <div class="score-text" *ngIf="!match.result_text">Match intelligence synchronizing...</div>
                   </ng-template>
                </div>

                <!-- Prediction Bridge (Visible if Live and Logged In) -->
                <div *ngIf="match.status === 'live' && isLoggedIn" class="prediction-module">
                   <ng-container *ngIf="livePredictionByMatchId[match.id]?.result as result; else loadingPred">
                      <div class="prob-bridge">
                        <div class="segment team1" [style.flex]="result.team1_win_probability">
                          <span>{{ (result.team1_win_probability * 100) | number:'1.0-0' }}%</span>
                        </div>
                        <div class="segment team2" [style.flex]="result.team2_win_probability">
                          <span>{{ (result.team2_win_probability * 100) | number:'1.0-0' }}%</span>
                        </div>
                      </div>
                      <div class="pred-label">AI Neural Prediction Snapshot</div>
                   </ng-container>
                   <ng-template #loadingPred>
                      <div class="pred-skeleton">Synchronizing with AI Models...</div>
                   </ng-template>
                </div>

                <div class="card-footer">
                  <span class="venue-tag" *ngIf="match.venue">{{ match.venue.name }}</span>
                  <span class="action-hint">ANALYZE FULL INTEL →</span>
                </div>
              </a>
            </div>

            <div *ngIf="!loading && matches.length === 0" class="empty-state">
              <div class="empty-icon">📡</div>
              <p>No active matches found in the selected feed.</p>
              <button (click)="load()" class="btn btn-secondary">Sync Global Feeds</button>
            </div>
          </div>
        </main>


        <!-- Right Intelligence Sidebar -->
        <aside class="intelligence-sidebar">
          
          <!-- News Pulse Widget -->
          <section class="widget news-pulse">
            <div class="widget-header">
              <h3>Global News Pulse</h3>
              <span class="live-pill">Live Feed</span>
            </div>
            <div class="widget-body">
              <div *ngIf="newsLoading" class="skeleton-list">
                 <div class="skeleton-item"></div>
                 <div class="skeleton-item"></div>
              </div>
              <div *ngFor="let item of news" class="news-item">
                <div class="news-meta">
                  <span class="news-source">{{ item.source }}</span>
                  <span class="news-time">Just now</span>
                </div>
                <h4>{{ item.title }}</h4>
              </div>
            </div>
          </section>

          <!-- ICC Rankings Widget -->
          <section class="widget ranking-widget">
            <div class="widget-header">
              <h3>ICC T20 Rankings</h3>
              <span class="year-pill">2026</span>
            </div>
            <div class="widget-body">
              <div *ngIf="standingsLoading" class="skeleton-list">
                 <div class="skeleton-item"></div>
              </div>
              <table class="rank-table">
                <tr *ngFor="let rank of standings; let i = index">
                  <td class="rank-num">#{{ i + 1 }}</td>
                  <td class="rank-name">{{ rank.player }}</td>
                  <td class="rank-val">{{ rank.rating }}</td>
                </tr>
              </table>
            </div>
          </section>

          <!-- Trusted Sources Manifest -->
          <section class="widget trust-manifest">
            <div class="widget-header">
              <h3>Source Integrity</h3>
            </div>
            <div class="widget-body">
              <p>MatchMind aggregates real-time data from authoritative sports intelligence nodes:</p>
              <div class="source-cloud">
                <span class="source-node">Cricbuzz</span>
                <span class="source-node">ESPNcricinfo</span>
                <span class="source-node">Sportsmonks</span>
                <span class="source-node">RapidAPI Free</span>
                <span class="source-node">BBC Sport</span>
                <span class="source-node">Sky Sports</span>
              </div>
              <div class="conflict-check">
                <div class="check-icon">VALIDATED</div>
                <span>Conflict-Resolution Engine Active</span>
              </div>
            </div>
          </section>

        </aside>
      </div>
    </div>
  `,
  styles: [`
    .matches-intelligence {
      padding: 1rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    /* Hero Section */
    .intelligence-hero {
      background: 
        radial-gradient(circle at top right, rgba(94, 234, 212, 0.15), transparent 40%),
        linear-gradient(165deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.98));
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 20px;
      padding: 2.5rem;
      margin-bottom: 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 2rem;
    }

    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(94, 234, 212, 0.1);
      padding: 0.4rem 0.8rem;
      border-radius: 99px;
      margin-bottom: 1rem;
      border: 1px solid rgba(94, 234, 212, 0.2);
    }

    .hero-badge span {
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--color-primary);
      font-weight: 800;
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 8px #10b981;
      animation: pulse 2s infinite;
    }

    .intelligence-hero h1 {
      font-size: 2.25rem;
      font-weight: 900;
      margin: 0 0 0.5rem 0;
      background: linear-gradient(to right, #fff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .hero-stats-ribbon {
      margin-top: 1.5rem;
      display: flex;
      gap: 2rem;
    }

    .stat-pill {
      display: grid;
      gap: 0.25rem;
    }

    .stat-pill {
      display: grid;
      gap: 0.25rem;
      cursor: pointer;
      padding: 0.5rem 1rem;
      border-radius: 12px;
      transition: all 0.2s;
      position: relative;
    }
    
    .stat-pill:hover { background: rgba(255,255,255,0.05); }
    .stat-pill.active { background: rgba(94, 234, 212, 0.1); border: 1px solid rgba(94, 234, 212, 0.2); }

    .live-indicator {
      position: absolute;
      top: 5px;
      right: 5px;
      width: 8px;
      height: 8px;
      background: #ef4444;
      border-radius: 50%;
      box-shadow: 0 0 10px #ef4444;
      animation: pulse 2s infinite;
    }

    .stat-pill label {
      font-size: 0.65rem;
      text-transform: uppercase;
      color: var(--text-secondary);
      letter-spacing: 0.05em;
    }

    .stat-pill strong {
      font-size: 1.25rem;
      color: #fff;
    }

    .stat-pill.live strong { color: #ef4444; }

    .hero-filters {
      display: flex;
      gap: 1rem;
    }

    .filter-group {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 0.5rem 1rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .search-box { flex: 1; min-width: 250px; padding: 0.3rem 0.5rem 0.3rem 1rem; }
    
    .dashboard-input {
      background: transparent;
      border: none;
      color: #fff;
      font-size: 0.85rem;
      width: 100%;
      outline: none;
    }

    .search-btn {
      background: var(--color-primary);
      color: #000;
      border: none;
      border-radius: 8px;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s;
    }

    .search-btn:hover { transform: scale(1.05); }

    .dashboard-select {
      background: transparent;
      border: none;
      color: #fff;
      font-size: 0.85rem;
      font-weight: 600;
      outline: none;
      cursor: pointer;
    }

    .dashboard-select option {
      background: #1e293b; 
      color: #fff;
    }

    /* Layout & Tabs */
    .section-tabs {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1.5rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 0.75rem;
      font-weight: 800;
      padding: 0.6rem 1.25rem;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s;
      letter-spacing: 0.1em;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.03); }
    .tab-btn.active { color: var(--color-primary); background: rgba(94, 234, 212, 0.1); }

    .count-badge {
      background: #ef4444;
      color: #fff;
      font-size: 0.6rem;
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
      font-weight: 900;
    }

    .tab-spacer { flex: 1; }

    .refresh-indicator {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      opacity: 0;
      transition: opacity 0.3s;
      pointer-events: none;
    }

    .refresh-indicator.visible { opacity: 1; }

    .refresh-indicator span { font-size: 0.7rem; font-weight: 700; color: var(--color-primary); text-transform: uppercase; }

    .spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(94, 234, 212, 0.2);
      border-top-color: var(--color-primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    /* Match Cards Refined */
    .score-preview {
      background: rgba(0,0,0,0.2);
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 1.5rem;
    }

    .score-display { display: grid; gap: 0.5rem; }
    .score-row { display: flex; align-items: center; gap: 0.75rem; font-size: 0.85rem; }
    .score-row span { color: rgba(255,255,255,0.6); flex: 1; }
    .score-row strong { color: #fff; font-weight: 800; }
    .score-row .overs { font-size: 0.7rem; color: var(--color-primary); opacity: 0.8; }
    .score-text { font-size: 0.8rem; color: #94a3b8; font-style: italic; }

    .match-time { font-size: 0.7rem; color: #64748b; font-weight: 700; }

    .score-val { display: flex; align-items: center; gap: 0.75rem; }
    .crr-tag {
       background: rgba(16, 185, 129, 0.1);
       color: #10b981;
       font-size: 0.65rem;
       font-weight: 900;
       padding: 0.1rem 0.4rem;
       border-radius: 4px;
       border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .live-commentary {
       margin-top: 0.75rem;
       padding: 0.6rem 0.8rem;
       background: rgba(255,255,255,0.03);
       border-radius: 6px;
       font-size: 0.75rem;
       color: #94a3b8;
       border-left: 2px solid #10b981;
       font-style: italic;
    }
    .team-name { color: #94a3b8; min-width: 100px; display: inline-block; }

    .badge .dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      background: currentColor;
      border-radius: 50%;
      margin-right: 4px;
      vertical-align: middle;
      box-shadow: 0 0 5px currentColor;
    }

    .vs-divider {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      width: 40px;
    }

    .vs-text { font-weight: 950; font-size: 0.7rem; color: rgba(255,255,255,0.1); }
    .vs-line { width: 1px; height: 30px; background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.05), transparent); }

    .venue-tag { opacity: 0.5; }
    .action-hint { color: var(--color-primary); opacity: 1 !important; letter-spacing: 0.05em; }

    .empty-state {
      padding: 5rem 2rem;
      text-align: center;
      background: rgba(30, 41, 59, 0.2);
      border: 1px dashed rgba(255,255,255,0.1);
      border-radius: 24px;
    }

    .empty-icon { font-size: 3rem; margin-bottom: 1.5rem; opacity: 0.3; }

    .prediction-module {
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px dashed rgba(255,255,255,0.1);
    }

    .prob-bridge {
      display: flex;
      height: 24px;
      border-radius: 6px;
      overflow: hidden;
      margin-bottom: 0.5rem;
    }

    .segment { display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 900; color: #fff; }
    .team1 { background: #10b981; }
    .team2 { background: #f59e0b; }

    .pred-label { font-size: 0.6rem; text-transform: uppercase; color: var(--color-primary); letter-spacing: 0.1em; font-weight: 800; }

    .card-footer {
      display: flex;
      justify-content: space-between;
      margin-top: 1.5rem;
      font-size: 0.75rem;
      color: var(--color-primary);
      font-weight: 700;
      opacity: 0.6;
    }

    /* Widgets */
    .widget {
      background: rgba(15, 23, 42, 0.4);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 16px;
      margin-bottom: 1.5rem;
      overflow: hidden;
    }

    .widget-header {
      padding: 1.25rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .widget-header h3 { font-size: 0.9rem; margin: 0; font-weight: 800; }

    .live-pill, .year-pill {
      font-size: 0.6rem;
      padding: 0.2rem 0.5rem;
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
      border-radius: 4px;
      font-weight: 900;
      text-transform: uppercase;
    }

    .widget-body { padding: 1.25rem; }

    .news-item {
      padding-bottom: 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.03);
      margin-bottom: 1rem;
    }

    .news-meta { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.4rem; }
    .news-source { font-size: 0.6rem; color: var(--color-primary); font-weight: 800; text-transform: uppercase; }
    .news-time { font-size: 0.6rem; color: var(--text-secondary); }
    .news-item h4 { font-size: 0.85rem; margin: 0; line-height: 1.4; color: #cbd5e1; }

    .rank-table { width: 100%; border-collapse: collapse; }
    .rank-table td { padding: 0.6rem 0; font-size: 0.85rem; border-bottom: 1px solid rgba(255,255,255,0.03); }
    .rank-num { width: 40px; color: var(--color-primary); font-weight: 800; }
    .rank-val { text-align: right; font-weight: 700; color: #fff; }

    .source-cloud { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }
    .source-node {
      font-size: 0.65rem;
      background: rgba(255,255,255,0.05);
      padding: 0.3rem 0.6rem;
      border-radius: 4px;
      color: var(--text-secondary);
    }

    .conflict-check {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.7rem;
      color: #10b981;
      font-weight: 700;
      margin-top: 1rem;
    }

    .sync-status-box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .sync-text { font-size: 0.75rem; color: #64748b; font-style: italic; }
    .manual-sync-mini {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      color: var(--color-primary);
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s;
    }
    .manual-sync-mini:hover { background: var(--color-primary); color: #000; scale: 1.1; }

    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.2); }
      100% { opacity: 1; transform: scale(1); }
    }
  `],
})
export class MatchListComponent implements OnInit, OnDestroy {
  isLoggedIn = false;
  matches: Match[] = [];
  activeTab = ''; // '' | 'live' | 'upcoming' | 'complete'
  status = '';
  format = '';
  searchQuery = '';
  loading = false;
  error = '';
  livePredictionByMatchId: Record<number, PredictionJob | null> = {};
  liveSocketConnectedByMatchId: Record<number, boolean> = {};
  private liveRefreshInterval: ReturnType<typeof setInterval> | null = null;
  private activeLiveMatchIds: number[] = [];
  liveSocketCleanupByMatchId: Record<number, () => void> = {};
  private refreshTimer: any;
  
  // Intelligence Data
  news: CricketNews[] = [];
  standings: InternationalStanding[] = [];
  topPerformers: TopPlayer[] = [];
  newsLoading = false;
  standingsLoading = false;
  performersLoading = false;

  get liveVisibleCount(): number {
    return this.matches.filter((match) => match.status === 'live').length;
  }

  get upcomingVisibleCount(): number {
    return this.matches.filter((match) => match.status === 'upcoming').length;
  }

  get completedVisibleCount(): number {
    return this.matches.filter((match) => match.status === 'complete').length;
  }

  constructor(private api: ApiService, private liveSocket: LivePredictionSocketService, private auth: AuthService) {}

  ngOnInit(): void {
    this.isLoggedIn = this.auth.isLoggedIn();
    this.load();
    this.loadIntelligence();

    // Super Lively Sync: Refresh match feed every 15s to catch score changes
    this.refreshTimer = setInterval(() => {
      this.load(true);
    }, 15000);
  }

  loadIntelligence(): void {
    this.newsLoading = true;
    this.standingsLoading = true;
    this.performersLoading = true;

    // Fetch News
    this.api.getCricketNews().subscribe({
      next: (res) => {
        this.news = res.results.slice(0, 5);
        this.newsLoading = false;
      },
      error: () => this.newsLoading = false
    });

    // Fetch Standings
    this.api.getInternationalStandings('t20').subscribe({
      next: (res) => {
        this.standings = res.results.slice(0, 5);
        this.standingsLoading = false;
      },
      error: () => this.standingsLoading = false
    });

    // Fetch Top Performers
    this.api.getTopPlayers('runs', 5).subscribe({
      next: (res) => {
        this.topPerformers = res.results;
        this.performersLoading = false;
      },
      error: () => this.performersLoading = false
    });
  }

  ngOnDestroy(): void {
    this.stopLiveRefresh();
  }

  onSyncMatch(event: Event, matchId: number): void {
    event.preventDefault();
    event.stopPropagation();
    this.api.triggerMatchSync(matchId).subscribe({
      next: () => {
        this.load(true);
      },
      error: () => console.error('Manual sync failed')
    });
  }

  setTab(tab: string): void {
    this.activeTab = tab;
    this.status = tab;
    this.load();
  }

  load(silent = false): void {
    if (!silent) this.loading = true;
    this.error = '';
    const filters: { status?: string; format?: string; search?: string } = {};
    if (this.status) filters.status = this.status;
    if (this.format) filters.format = this.format;
    if (this.searchQuery) filters.search = this.searchQuery;

    this.api.getMatches(filters).subscribe({
      next: (response) => {
        let sortedResults = response.results;
        
        // Custom sorting for 'All Feed' mode
        if (!this.activeTab) {
          const statusOrder: Record<string, number> = {
            'live': 0,
            'complete': 1,
            'upcoming': 2,
            'abandoned': 3
          };
          
          sortedResults = [...response.results].sort((a, b) => {
            const orderA = statusOrder[a.status] ?? 4;
            const orderB = statusOrder[b.status] ?? 4;
            
            if (orderA !== orderB) {
              return orderA - orderB;
            }
            
            // For same status, sort by date (descending for completed, ascending for upcoming)
            const dateA = new Date(a.match_date || 0).getTime();
            const dateB = new Date(b.match_date || 0).getTime();
            
            if (a.status === 'upcoming') {
              return dateA - dateB; // Closest upcoming first
            }
            return dateB - dateA; // Most recent completed first
          });
        }

        this.matches = sortedResults;
        this.syncLivePredictionRefresh();
        this.loading = false;
      },
      error: () => {
        this.matches = [];
        this.stopLiveRefresh();
        this.loading = false;
        this.error = 'Unable to load matches right now.';
      },
    });
  }

  private syncLivePredictionRefresh(): void {
    if (!this.isLoggedIn) {
      this.livePredictionByMatchId = {};
      this.stopLiveRefresh();
      return;
    }

    this.activeLiveMatchIds = this.matches.filter((match) => match.status === 'live').map((match) => match.id);
    const activeSet = new Set(this.activeLiveMatchIds);

    for (const key of Object.keys(this.liveSocketCleanupByMatchId)) {
      const matchId = Number(key);
      if (!activeSet.has(matchId)) {
        this.liveSocketCleanupByMatchId[matchId]?.();
        delete this.liveSocketCleanupByMatchId[matchId];
        delete this.liveSocketConnectedByMatchId[matchId];
      }
    }

    if (this.activeLiveMatchIds.length === 0) {
      this.livePredictionByMatchId = {};
      this.stopLiveRefresh();
      return;
    }

    for (const matchId of this.activeLiveMatchIds) {
      if (!this.liveSocketCleanupByMatchId[matchId]) {
        this.liveSocketCleanupByMatchId[matchId] = this.liveSocket.subscribeToMatch(matchId, {
          onOpen: () => {
            this.liveSocketConnectedByMatchId[matchId] = true;
          },
          onClose: () => {
            this.liveSocketConnectedByMatchId[matchId] = false;
          },
          onError: () => {
            this.liveSocketConnectedByMatchId[matchId] = false;
          },
          onPrediction: (prediction) => {
            this.liveSocketConnectedByMatchId[matchId] = true;
            this.livePredictionByMatchId[matchId] = prediction;
          },
        });
      }
    }

    this.refreshLivePredictions();
    if (!this.liveRefreshInterval) {
      this.liveRefreshInterval = setInterval(() => {
        this.refreshLivePredictions();
      }, 15000);
    }
  }

  private refreshLivePredictions(): void {
    for (const matchId of this.activeLiveMatchIds) {
      if (this.liveSocketConnectedByMatchId[matchId]) {
        continue;
      }
      this.api.getLatestPredictionForMatch(matchId, 'live').subscribe({
        next: (prediction) => {
          this.livePredictionByMatchId[matchId] = prediction;
        },
        error: () => {
          this.livePredictionByMatchId[matchId] = null;
        },
      });
    }
  }

  private stopLiveRefresh(): void {
    if (this.liveRefreshInterval) {
      clearInterval(this.liveRefreshInterval);
      this.liveRefreshInterval = null;
    }
    for (const key of Object.keys(this.liveSocketCleanupByMatchId)) {
      const matchId = Number(key);
      this.liveSocketCleanupByMatchId[matchId]?.();
      delete this.liveSocketCleanupByMatchId[matchId];
      delete this.liveSocketConnectedByMatchId[matchId];
    }
    this.activeLiveMatchIds = [];
  }
}
