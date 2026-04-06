import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ApiService, Match, PredictionJob, MatchScorecard, BatsmanStats, BowlerStats, TeamAnalytics, CricketNews } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-match-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-container animate-fade-up match-intelligence-detail">
      
      <!-- Premium Detail Hero -->
      <section class="card detail-hero-v2" *ngIf="match">
        <div class="hero-main">
          <div class="match-meta">
            <span class="badge badge--{{ match.status === 'live' ? 'live' : (match.status === 'complete' ? 'complete' : 'upcoming') }}">{{ match.status | uppercase }}</span>
            <span class="format-label">{{ match.format | uppercase }}</span>
          </div>
          
          <div class="vs-identity">
            <div class="team">
              <div class="logo-box">
                <img [src]="match.team1?.logo_url || 'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?w=120'" [alt]="match.team1?.name">
              </div>
              <h2 style="color: #fff; font-size: 1.5rem; margin: 0; font-weight: 800;">{{ match.team1?.name || 'Unknown' }}</h2>
              <div class="innings-display" *ngIf="match.scorecards && match.scorecards.length > 0">
                 <strong>{{ match.scorecards[0].total_runs }}/{{ match.scorecards[0].total_wickets }}</strong>
                 <span class="overs">({{ match.scorecards[0].total_overs }} ov)</span>
              </div>
            </div>
            <div class="divider">VS</div>
            <div class="team">
              <div class="logo-box">
                <img [src]="match.team2?.logo_url || 'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?w=120'" [alt]="match.team2?.name">
              </div>
              <h2 style="color: #fff; font-size: 1.5rem; margin: 0; font-weight: 800;">{{ match.team2?.name || 'Unknown' }}</h2>
              <div class="innings-display" *ngIf="match.scorecards && match.scorecards.length > 1">
                 <strong>{{ match.scorecards[1].total_runs }}/{{ match.scorecards[1].total_wickets }}</strong>
                 <span class="overs">({{ match.scorecards[1].total_overs }} ov)</span>
              </div>
            </div>
          </div>

          <div *ngIf="match.live_status_text || match.result_text" class="result-strip">
             {{ match.live_status_text || match.result_text }}
          </div>
        </div>

        <div class="hero-sidebar">
           <div class="venue-info">
              <label>Match Environment</label>
              <strong>{{ match.venue?.name }}</strong>
              <span>{{ match.venue?.city }}, {{ match.venue?.country }}</span>
           </div>
           
           <div class="weather-mini" *ngIf="weather">
              <div class="temp">{{ weather.temperature }}°C</div>
              <div class="cond">
                <span *ngIf="weather.weathercode === 0">Clear Skies</span>
                <span *ngIf="weather.weathercode > 0 && weather.weathercode <= 3">Partly Cloudy</span>
                <span *ngIf="weather.weathercode > 3 && weather.weathercode <= 69">Rain Expected</span>
                <span *ngIf="weather.weathercode >= 70">Storm Warning</span>
              </div>
           </div>
        </div>
      </section>

      <div class="detail-grid" *ngIf="match">
        <!-- Left Column: Core Data -->
        <main class="primary-data">
          
          <!-- Super Live Match Center (Google Style) -->
          <section class="card super-live-panel animate-fade-in" *ngIf="match.status === 'live'">
             <div class="live-context">
                <div class="status-big">{{ match.live_status_text || 'Match in progress...' }}</div>
                <div class="live-rates" *ngIf="match.scorecards?.[0] as sc">
                   <div class="rate">CRR: <strong>{{ sc.crr }}</strong></div>
                   <div class="rate" *ngIf="sc.rrr">RRR: <strong class="highlight">{{ sc.rrr }}</strong></div>
                </div>
             </div>

             <div class="mini-scorecard">
                <!-- Batting Stats -->
                <div class="mini-group batters">
                   <div class="mini-row" *ngFor="let b of match.current_batters">
                      <div class="player">
                        <span class="dot" *ngIf="b.on_strike"></span>
                        <span class="name">{{ b.name }}</span>
                      </div>
                      <div class="stats"><strong>{{ b.runs }}</strong>({{ b.balls }})</div>
                   </div>
                </div>

                <!-- Bowling Stats -->
                <div class="mini-group bowlers">
                   <div class="mini-row" *ngFor="let bw of match.current_bowlers">
                      <div class="player">
                        <span class="name">{{ bw.name }}</span>
                      </div>
                      <div class="stats"><strong>{{ bw.wickets }}-{{ bw.runs }}</strong> ({{ bw.overs }})</div>
                   </div>
                </div>

                <!-- Recent Commentary Strip -->
                <div class="mini-group recent">
                  <div class="recent-label">RECENT</div>
                  <div class="ball-strip">
                     <span class="ball" *ngFor="let b of (match.last_balls || '').split(' ')" [class.wicket]="b === 'W'" [class.boundary]="b === '4' || b === '6'">{{ b }}</span>
                  </div>
                </div>
             </div>
          </section>

          <!-- AI Prediction Hub -->
          <section class="card prediction-hub" *ngIf="isLoggedIn && match.status !== 'complete'">
            <div class="section-label">Neural Match Analysis</div>
            
            <div *ngIf="latestPrediction?.result as result; else predLoader" class="prediction-content">
               <div class="prob-visualization">
                  <div class="prob-box">
                    <label>{{ result.team1.name }}</label>
                    <div class="val">{{ (result.team1_win_probability * 100) | number:'1.0-0' }}%</div>
                  </div>
                  <div class="bridge-container">
                    <div class="bridge">
                      <div class="fill t1" [style.width.%]="result.team1_win_probability * 100"></div>
                      <div class="fill t2" [style.width.%]="result.team2_win_probability * 100"></div>
                    </div>
                  </div>
                  <div class="prob-box right">
                    <label>{{ result.team2.name }}</label>
                    <div class="val">{{ (result.team2_win_probability * 100) | number:'1.0-0' }}%</div>
                  </div>
               </div>
               <div class="trust-metric">System Confidence: {{ result.confidence_score | number:'1.2-2' }}</div>
            </div>
            <ng-template #predLoader>
               <div class="pred-skeleton">Synchronizing Neural Weights...</div>
            </ng-template>
          </section>

          <!-- Super Scorecard Explorer -->
          <section class="card scorecard-explorer" *ngIf="(match.scorecards?.length ?? 0) > 0">
            <div class="scorecard-header">
              <div class="section-label">Advanced Match Center</div>
              
              <!-- Innings Tabs -->
              <div class="innings-tabs">
                <button 
                  *ngFor="let sc of match.scorecards; let i = index" 
                  (click)="selectedInningsIndex = i"
                  [class.active]="selectedInningsIndex === i"
                  class="tab-btn">
                  {{ i + 1 }}{{ i === 0 ? 'st' : (i === 1 ? 'nd' : (i === 2 ? 'rd' : 'th')) }} Innings
                </button>
              </div>
            </div>
            
            <div *ngFor="let sc of match.scorecards; let i = index" 
                 class="innings-block animate-fade-in"
                 [style.display]="selectedInningsIndex === i ? 'block' : 'none'">
               <div class="innings-summary">
                <div class="bat-identity">
                  <span class="num">{{ sc.innings_number }}{{ sc.innings_number === 1 ? 'st' : (sc.innings_number === 2 ? 'nd' : (sc.innings_number === 3 ? 'rd' : 'th')) }}</span>
                  <strong>{{ sc.batting_team?.name || 'Innings ' + sc.innings_number }}</strong>
                </div>
                <div class="main-stats">
                  <div class="stat">
                    <span class="lbl">Runs</span>
                    <span class="val highlight-runs">{{ sc.total_runs }}/{{ sc.total_wickets }}</span>
                  </div>
                  <div class="stat">
                    <span class="lbl">Overs</span>
                    <span class="val">{{ sc.total_overs }}</span>
                  </div>
                  <div class="stat">
                    <span class="lbl">RR</span>
                    <span class="val">{{ sc.run_rate }}</span>
                  </div>
                </div>
              </div>

              <!-- Batting Performance -->
              <div class="table-title">Batting Performance</div>
              <div class="stats-table-wrap">
                <table class="stats-table">
                  <thead>
                    <tr>
                      <th>Batsman</th>
                      <th class="num">R</th>
                      <th class="num">B</th>
                      <th class="num">4s</th>
                      <th class="num">6s</th>
                      <th class="num">SR</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let b of sc.batting_data">
                      <td>
                        <div class="player-cell">
                          <span class="name">{{ b.batsman || b.batsmanName || b.name || 'Unknown' }}</span>
                          <span class="status">{{ b.outdec || b.outDesc || b.status || 'Not out' }}</span>
                        </div>
                      </td>
                      <td class="num highlight-runs">{{ b.runs ?? b.r ?? 0 }}</td>
                      <td class="num grey">{{ b.balls ?? b.b ?? 0 }}</td>
                      <td class="num grey">{{ b.fours ?? b.f4 ?? b['4s'] ?? 0 }}</td>
                      <td class="num grey">{{ b.sixes ?? b.s6 ?? b['6s'] ?? 0 }}</td>
                      <td class="num">
                        <div class="sr-cell">
                          <span class="val" [class.highlight]="(b.strikeRate || b.strike_rate || b.sr || b.strkrate || 0) > 150">{{ b.strikeRate || b.strike_rate || b.sr || b.strkrate || 0 }}</span>
                          <div class="sr-bar">
                             <div class="fill" [style.width.%]="(b.strikeRate || b.strike_rate || b.sr || b.strkrate || 0) / 2" [class.hot]="(b.strikeRate || b.strike_rate || b.sr || b.strkrate || 0) > 150"></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Bowling Intelligence -->
              <div class="table-title">Bowling Intelligence</div>
              <div class="stats-table-wrap" *ngIf="sc.bowling_data?.length">
                <table class="stats-table">
                  <thead>
                    <tr>
                      <th>Bowler</th>
                      <th class="num">O</th>
                      <th class="num">M</th>
                      <th class="num">R</th>
                      <th class="num">W</th>
                      <th class="num">ECO</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let bw of sc.bowling_data">
                      <td>{{ bw.bowler || bw.bowlerName || bw.name || 'Unknown' }}</td>
                      <td class="num">{{ bw.overs ?? bw.o ?? 0 }}</td>
                      <td class="num grey">{{ bw.maidens ?? bw.m ?? 0 }}</td>
                      <td class="num grey">{{ bw.runs ?? bw.r ?? 0 }}</td>
                      <td class="num highlight-wickets">{{ bw.wickets ?? bw.w ?? 0 }}</td>
                      <td class="num">
                         <div class="sr-cell">
                           <span class="val">{{ bw.economy ?? bw.eco ?? 0 }}</span>
                           <div class="sr-bar eco">
                              <div class="fill" [style.width.%]="(bw.economy || bw.eco || 0) * 8"></div>
                           </div>
                         </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <div *ngIf="match && (!match.scorecards || match.scorecards.length === 0)" class="card empty-data">
             <p>Real-time scorecard data currently synchronizing with global nodes.</p>
          </div>

        </main>

        <!-- Right Column: Contextual Intel -->
        <aside class="context-intel">
          
          <!-- Team Momentum Widget -->
          <section class="card widget momentum-widget">
            <div class="widget-header">Strategic Momentum</div>
            <div class="widget-body">
              <div class="momentum-row" *ngFor="let team of [match.team1, match.team2]">
                <div class="team-meta">
                  <strong>{{ team?.name || 'Unknown' }}</strong>
                  <span class="form-strip" *ngIf="team && getTeamForm(team.name) as form">
                    <span *ngFor="let r of form" class="result {{ r }}">{{ r }}</span>
                  </span>
                </div>
              </div>
            </div>
          </section>

          <!-- Recent Intelligence (News) -->
          <section class="card widget news-widget" *ngIf="teamNews.length > 0">
            <div class="widget-header">Recent Intelligence</div>
            <div class="widget-body">
              <div class="news-intel-item" *ngFor="let item of teamNews.slice(0, 3)">
                <div class="news-source">{{ item.source }}</div>
                <h4 style="font-size: 0.85rem; margin: 0; line-height: 1.4; color: #cbd5e1;">{{ item.title }}</h4>
              </div>
            </div>
          </section>

          <!-- Map Surface -->
          <section class="card widget map-widget" *ngIf="mapUrl">
             <div class="widget-header">Geographic Data</div>
             <div class="map-surface">
                <iframe width="100%" height="200" frameborder="0" [src]="mapUrl" style="border: none;"></iframe>
             </div>
          </section>

        </aside>
      </div>
    </div>
  `,
  styles: [`
    .match-intelligence-detail {
       max-width: 1200px;
       margin: 0 auto;
       padding: 1rem;
    }

    /* Hero Refined */
    .detail-hero-v2 {
       background: 
         radial-gradient(circle at 90% 10%, rgba(94, 234, 212, 0.15), transparent 40%),
         linear-gradient(165deg, rgba(15, 23, 42, 0.98), rgba(20, 30, 50, 0.98));
       border: 1px solid rgba(255,255,255,0.06);
       border-radius: 24px;
       padding: 2.5rem;
       margin-bottom: 2rem;
       display: flex;
       justify-content: space-between;
       gap: 3rem;
       box-shadow: 0 25px 60px rgba(0,0,0,0.4);
    }

    .hero-main { flex: 1; }

    .vs-identity {
       display: flex;
       align-items: center;
       gap: 2.5rem;
       margin: 2rem 0;
    }

    .team {
       display: flex;
       flex-direction: column;
       align-items: center;
       gap: 1rem;
       text-align: center;
       width: 160px;
    }

    .logo-box {
       width: 90px;
       height: 90px;
       background: rgba(255,255,255,0.03);
       border: 1px solid rgba(255,255,255,0.08);
       border-radius: 50%;
       padding: 1rem;
       display: flex;
       align-items: center;
       justify-content: center;
       backdrop-filter: blur(10px);
    }

    .logo-box img { width: 100%; height: 100%; object-fit: contain; }

    .divider { font-size: 0.8rem; font-weight: 900; color: rgba(255,255,255,0.1); }

    .result-strip {
       background: rgba(16, 185, 129, 0.1);
       color: #10b981;
       padding: 0.6rem 1.2rem;
       border-radius: 12px;
       display: inline-block;
       font-weight: 700;
       border: 1px solid rgba(16, 185, 129, 0.2);
    }

    .hero-sidebar {
       width: 280px;
       border-left: 1px solid rgba(255,255,255,0.08);
       padding-left: 2rem;
       display: flex;
       flex-direction: column;
       gap: 2rem;
    }

    .venue-info label { font-size: 0.65rem; text-transform: uppercase; color: #10b981; letter-spacing: 0.1em; font-weight: 800; }
    .venue-info strong { display: block; font-size: 1.1rem; margin-top: 0.5rem; color: #fff; }
    .venue-info span { font-size: 0.8rem; color: rgba(255,255,255,0.6); }

    .weather-mini .temp { font-size: 2rem; font-weight: 900; color: #38bdf8; }
    .weather-mini .cond { font-size: 0.75rem; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; }

    /* Layout */
    .detail-grid {
       display: grid;
       grid-template-columns: 1fr 320px;
       gap: 2rem;
    }

    @media (max-width: 1024px) {
       .detail-hero-v2 { flex-direction: column; gap: 2rem; }
       .hero-sidebar { width: 100%; border-left: none; border-top: 1px solid rgba(255,255,255,0.08); padding: 2rem 0 0 0; flex-direction: row; justify-content: space-between; }
       .detail-grid { grid-template-columns: 1fr; }
    }

    .section-label {
       font-size: 0.8rem;
       font-weight: 800;
       text-transform: uppercase;
       letter-spacing: 0.15em;
       color: #10b981;
       margin-bottom: 2rem;
       opacity: 0.8;
    }

    .prediction-hub { padding: 2.5rem; margin-bottom: 2rem; background: rgba(30, 41, 59, 0.4); border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); }

    .prob-visualization {
       display: flex;
       align-items: center;
       gap: 2rem;
    }

    .prob-box { flex: 0 0 100px; text-align: left; }
    .prob-box.right { text-align: right; }
    .prob-box label { font-size: 0.75rem; color: rgba(255,255,255,0.6); display: block; margin-bottom: 0.5rem; }
    .prob-box .val { font-size: 2.5rem; font-weight: 950; color: #fff; line-height: 1; }

    .bridge-container { flex: 1; height: 32px; background: rgba(0,0,0,0.2); border-radius: 8px; overflow: hidden; }
    .bridge { display: flex; height: 100%; }
    .fill { height: 100%; transition: width 0.8s ease; }
    .fill.t1 { background: #10b981; }
    .fill.t2 { background: #f59e0b; }

    .trust-metric { margin-top: 1.5rem; font-size: 0.7rem; color: rgba(255,255,255,0.6); text-align: center; text-transform: uppercase; font-weight: 700; }

    /* Scorecard Explorer */
    .scorecard-explorer { 
       padding: 2rem; 
       background: rgba(30, 41, 59, 0.4); 
       border-radius: 24px; 
       border: 1px solid rgba(255,255,255,0.06);
       box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    
    .innings-block { margin-bottom: 4rem; }
    .innings-summary {
       display: flex;
       justify-content: space-between;
       align-items: flex-end;
       margin-bottom: 2rem;
       padding-bottom: 1.5rem;
       border-bottom: 1px solid rgba(255,255,255,0.08);
    }
 
    .bat-identity .num { 
       font-size: 0.75rem; 
       background: #10b981; 
       color: #000; 
       padding: 0.3rem 0.6rem; 
       border-radius: 6px; 
       font-weight: 900; 
       margin-right: 1rem; 
       vertical-align: middle; 
       box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }
    .bat-identity strong { font-size: 1.75rem; color: #fff; letter-spacing: -0.02em; }
 
    .main-stats { display: flex; gap: 3rem; }
    .stat .lbl { font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.1em; display: block; margin-bottom: 0.25rem; }
    .stat .val { font-size: 1.5rem; font-weight: 900; color: #fff; }
 
    .stats-table-wrap { 
       background: rgba(15, 23, 42, 0.3); 
       border-radius: 16px; 
       overflow: hidden; 
       border: 1px solid rgba(255,255,255,0.04);
       margin-bottom: 2rem;
    }
    
    .stats-table { width: 100%; border-collapse: collapse; }
    .stats-table th { 
       text-align: left; 
       font-size: 0.65rem; 
       color: var(--color-primary); 
       text-transform: uppercase; 
       padding: 1rem 1.25rem; 
       background: rgba(94, 234, 212, 0.03); 
       letter-spacing: 0.1em;
       font-weight: 800;
    }
    .stats-table td { 
       padding: 1rem 1.25rem; 
       font-size: 0.9rem; 
       border-bottom: 1px solid rgba(255,255,255,0.02); 
       color: #cbd5e1; 
       font-weight: 500;
    }
    .stats-table tr:last-child td { border-bottom: none; }
    .stats-table tr:hover td { background: rgba(255,255,255,0.02); }
    
    .stats-table .num { text-align: right; }
    .num.highlight { color: #10b981; font-weight: 800; }
    .num.highlight-runs { color: #f59e0b; font-weight: 700; }
    .num.highlight-wickets { color: #ef4444; font-weight: 950; }
    .num.grey { color: rgba(255,255,255,0.6); font-size: 0.8rem; }
    
    .table-title {
       font-size: 0.7rem;
       font-weight: 950;
       letter-spacing: 0.2em;
       color: var(--color-primary);
       opacity: 0.9;
       margin: 2.5rem 0 1rem 0;
       display: flex;
       align-items: center;
       gap: 1.5rem;
       text-transform: uppercase;
    }
    .table-title::after { content: ''; flex: 1; height: 1px; background: linear-gradient(to right, rgba(94, 234, 212, 0.2), transparent); }
 
    .empty-data { 
       padding: 4rem; 
       text-align: center; 
       color: rgba(255,255,255,0.4); 
       border-radius: 24px; 
       border: 1px dashed rgba(255,255,255,0.1);
       font-size: 1rem;
       font-weight: 600;
       background: rgba(30, 41, 59, 0.2);
    }

    /* Tabs & Advanced UI */
    .scorecard-header {
       display: flex;
       justify-content: space-between;
       align-items: center;
       margin-bottom: 2.5rem;
    }
    .innings-tabs {
       display: flex;
       background: rgba(0,0,0,0.2);
       padding: 0.4rem;
       border-radius: 12px;
       gap: 0.5rem;
    }
    .tab-btn {
       padding: 0.6rem 1.25rem;
       border: none;
       background: transparent;
       color: rgba(255,255,255,0.5);
       font-size: 0.75rem;
       font-weight: 800;
       border-radius: 8px;
       cursor: pointer;
       transition: all 0.3s ease;
       text-transform: uppercase;
       letter-spacing: 0.05em;
    }
    .tab-btn.active {
       background: #10b981;
       color: #000;
       box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    }
    .player-cell {
       display: flex;
       flex-direction: column;
    }
    .player-cell .status {
       font-size: 0.65rem;
       color: rgba(255,255,255,0.4);
       margin-top: 0.25rem;
       font-weight: 600;
    }
    .sr-cell {
       display: flex;
       flex-direction: column;
       align-items: flex-end;
       gap: 0.4rem;
    }
    .sr-bar {
       width: 60px;
       height: 4px;
       background: rgba(255,255,255,0.1);
       border-radius: 2px;
       overflow: hidden;
    }
    .sr-bar .fill {
       height: 100%;
       background: #10b981;
       border-radius: 2px;
    }
    .sr-bar .fill.hot { background: #f43f5e; }
    .sr-bar.eco .fill { background: #38bdf8; }

    /* Super Live Panel (Google Style) */
    .super-live-panel {
       background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.8));
       border-left: 4px solid #10b981;
       margin-bottom: 2rem;
       padding: 1.5rem 2rem;
    }
    .live-context {
       display: flex;
       justify-content: space-between;
       align-items: center;
       margin-bottom: 1.5rem;
       padding-bottom: 1rem;
       border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .status-big { font-size: 1.1rem; font-weight: 800; color: #fff; }
    .live-rates { display: flex; gap: 2rem; font-size: 0.9rem; color: rgba(255,255,255,0.6); font-weight: 700; }
    .live-rates strong { color: #fff; margin-left: 0.25rem; }
    .rate .highlight { color: #f59e0b; }

    .mini-scorecard {
       display: grid;
       grid-template-columns: 1fr 1fr 1.2fr;
       gap: 3rem;
    }
    .mini-group { display: flex; flex-direction: column; gap: 0.5rem; }
    .mini-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; }
    .mini-row .player { display: flex; align-items: center; gap: 0.5rem; color: #cbd5e1; font-weight: 600; }
    .mini-row .player .dot { width: 6px; height: 6px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; }
    .mini-row .stats { color: rgba(255,255,255,0.8); }
    
    .recent-label { font-size: 0.65rem; color: rgba(255,255,255,0.4); font-weight: 900; letter-spacing: 0.1rem; margin-bottom: 0.4rem; }
    .ball-strip { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .ball { 
       width: 32px; height: 32px; background: rgba(0,0,0,0.3); border-radius: 50%; 
       display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 900; 
       color: #fff; border: 1px solid rgba(255,255,255,0.1);
    }
    .ball.wicket { background: #ef4444; border-color: #ef4444; }
    .ball.boundary { background: #10b981; border-color: #10b981; }
  `],
})
export class MatchDetailComponent implements OnInit, OnDestroy {
  isLoggedIn = false;
  match: Match | null = null;
  latestPrediction: PredictionJob | null = null;
  private predictionRefreshTimer: ReturnType<typeof setInterval> | null = null;
  private lastAutoTriggerAt = 0;
  
  weather: any = null;
  mapUrl: SafeResourceUrl | null = null;
  weatherLoading = false;
  
  // Advanced UI State
  selectedInningsIndex = 0;
  
  // Extra Intel
  team1Analytics: TeamAnalytics | null = null;
  team2Analytics: TeamAnalytics | null = null;
  teamNews: CricketNews[] = [];

  constructor(
    private route: ActivatedRoute, 
    private api: ApiService, 
    private auth: AuthService,
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {}

  ngOnDestroy(): void {
    if (this.predictionRefreshTimer) {
      clearInterval(this.predictionRefreshTimer);
      this.predictionRefreshTimer = null;
    }
  }

  ngOnInit(): void {
    this.isLoggedIn = this.auth.isLoggedIn();

    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) return;

    this.api.getMatch(id).subscribe({
      next: (response) => {
        this.match = response;
        
        // Load Venue Data
        if (this.match.venue && this.match.venue.city) {
          this.loadVenueData(this.match.venue.city);
        }

        // Load Team Intelligence
        this.loadTeamIntel();

        if (!this.isLoggedIn) {
          this.latestPrediction = null;
          return;
        }

        this.refreshPredictionAndAutostart(id);

        if (this.predictionRefreshTimer) {
          clearInterval(this.predictionRefreshTimer);
        }
        this.predictionRefreshTimer = setInterval(() => {
          this.refreshPredictionAndAutostart(id);
          this.refreshMatchData(id); // Poll full match data for LIVELY updates
        }, 10000);
      },
    });
  }

  private refreshMatchData(id: number): void {
     // For live matches, trigger a background pipeline sync to ensure we get latest CricAPI/RapidAPI data
     if (this.match?.status === 'live') {
       this.api.triggerMatchSync(id).subscribe({
         next: () => console.log('Background score sync triggered for match:', id),
         error: () => console.warn('Could not trigger background score sync')
       });
     }

     this.api.getMatch(id).subscribe(res => {
        this.match = res;
     });
  }

  private loadVenueData(city: string): void {
    this.weatherLoading = true;
    
    // Fallbacks if city is too generic or Nominatim fails
    let queryCity = city;
    // Nominatim Geocoding API (Free, No Auth required for limited local usage)
    this.http.get<any[]>(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(queryCity)}&format=json&limit=1`)
      .subscribe({
        next: (geoRes) => {
          if (geoRes && geoRes.length > 0) {
            const lat = parseFloat(geoRes[0].lat);
            const lon = parseFloat(geoRes[0].lon);
            
            // Set embedded interactive map URL
            const bbox = `${lon-0.08},${lat-0.08},${lon+0.08},${lat+0.08}`;
            const rawUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lon}`;
            this.mapUrl = this.sanitizer.bypassSecurityTrustResourceUrl(rawUrl);

            // Fetch live weather data using Open-Meteo (Free API, No Key)
            this.http.get<any>(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`)
              .subscribe({
                next: (weatherRes) => {
                  if (weatherRes && weatherRes.current_weather) {
                    this.weather = weatherRes.current_weather;
                  }
                  this.weatherLoading = false;
                },
                error: () => this.weatherLoading = false
              });
          } else {
            this.weatherLoading = false;
          }
        },
        error: () => this.weatherLoading = false
      });
  }

  private loadTeamIntel(): void {
    if (!this.match || !this.match.team1 || !this.match.team2) return;

    // Fetch Team Analytics for form
    this.api.getTeamAnalytics(this.match.team1.name).subscribe(res => this.team1Analytics = res);
    this.api.getTeamAnalytics(this.match.team2.name).subscribe(res => this.team2Analytics = res);

    // Fetch News for teams
    this.api.getCricketNews().subscribe(res => {
      const t1 = this.match?.team1?.name?.toLowerCase();
      const t2 = this.match?.team2?.name?.toLowerCase();
      const keywords = [t1, t2].filter(k => !!k) as string[];

      this.teamNews = res.results.filter(n => 
        keywords.some(k => n.title.toLowerCase().includes(k) || n.summary.toLowerCase().includes(k))
      );
    });
  }

  getTeamForm(teamName?: string): string[] | null {
    if (!this.match) return null;
    const analytics = teamName === this.match.team1?.name ? this.team1Analytics : this.team2Analytics;
    if (!analytics || !analytics.recent_form) return null;
    return analytics.recent_form.map(f => f.outcome.toUpperCase().charAt(0)).slice(0, 5);
  }

  private refreshPredictionAndAutostart(matchId: number): void {
    if (!this.isLoggedIn || !this.match) {
      return;
    }

    const isLive = this.match.status === 'live';
    const isUpcoming = this.match.status === 'upcoming';
    if (!isLive && !isUpcoming) {
      return;
    }

    const predictionType = isLive ? 'live' : 'pre_match';
    this.api.getLatestPredictionForMatch(matchId, predictionType).subscribe({
      next: (response) => {
        this.latestPrediction = response;
      },
      error: () => {
        this.latestPrediction = null;

        const now = Date.now();
        if (now - this.lastAutoTriggerAt < 30000) {
          return;
        }
        this.lastAutoTriggerAt = now;

        this.api.createPrediction(matchId, predictionType).subscribe({
          next: () => {},
          error: () => {}
        });
      },
    });
  }
}

