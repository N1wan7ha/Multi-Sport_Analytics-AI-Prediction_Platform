import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, Match, PipelineStatus, CricketNews } from '../../core/services/api.service';
import { PredictionJob } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

type MatchFormatFilter = 'all' | 't20' | 'odi' | 'test';
type MatchCategoryFilter = 'all' | 'international' | 'franchise' | 'domestic';
type NewsCategory = 'top' | 'trending' | 'editorial' | 'rankings';

interface PredictionCard {
  match: Match;
  loading: boolean;
  error: string;
  job: PredictionJob | null;
}

interface NewsBanner {
  id: number;
  title: string;
  summary: string;
  linkLabel: string;
  link: string;
  source?: string;
  image?: string;
  category: NewsCategory;
  timestamp?: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="page-container animate-fade-up">
      <section class="card hero-card" style="margin-bottom: 1rem;">
        <p class="hero-kicker">MatchMind Home</p>
        <h1>Cricket Pulse + AI Picks</h1>
        <p class="text-secondary" style="margin-top:0.45rem">
          Auto-generated prediction cards for top fixtures. No manual selection needed.
        </p>

        <div class="quick-stats">
          <div class="quick-stat">
            <span>Live Now</span>
            <strong>{{ liveNowCount }}</strong>
          </div>
          <div class="quick-stat">
            <span>Upcoming</span>
            <strong>{{ upcomingMatches.length }}</strong>
          </div>
          <div class="quick-stat">
            <span>Your Favorites</span>
            <strong>{{ favouriteTeamNames.length + favouritePlayerNames.length }}</strong>
          </div>
          <div class="quick-stat" *ngIf="isAdmin">
            <span>Model State</span>
            <strong>{{ pipelineStatus?.model_retraining_status || 'N/A' }}</strong>
          </div>
          <div class="quick-stat" *ngIf="!isAdmin">
            <span>News Loaded</span>
            <strong>{{ newsBanners.length }}</strong>
          </div>
        </div>

        <div class="filter-row">
          <div class="chip-set">
            <button
              *ngFor="let option of formatOptions"
              class="chip-btn"
              [class.chip-active]="formatFilter === option"
              (click)="setFormatFilter(option)"
            >
              {{ option === 'all' ? 'All Formats' : (option | uppercase) }}
            </button>
          </div>
          <div class="chip-set">
            <button
              *ngFor="let option of categoryOptions"
              class="chip-btn"
              [class.chip-active]="categoryFilter === option"
              (click)="setCategoryFilter(option)"
            >
              {{ option === 'all' ? 'All Types' : option }}
            </button>
          </div>
          <button class="btn btn-secondary" (click)="refreshAutoPredictions()" [disabled]="!isLoggedIn" *ngIf="isLoggedIn">
            Refresh AI Cards
          </button>
          <a *ngIf="!isLoggedIn" routerLink="/auth/login" class="btn btn-primary">
            Login for AI Predictions
          </a>
        </div>
      </section>

      <section class="card news-stage" style="margin-bottom: 1rem;">
        <div class="headline-ticker" *ngIf="!newsLoading && filteredNews.length > 0" (click)="openTickerStory()">
          <span class="ticker-label">Live Headlines</span>
          <div class="ticker-track">
            <span class="ticker-text">{{ currentTickerHeadline?.title }}</span>
          </div>
          <span class="ticker-hint">Open</span>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap;">
          <h3 style="margin:0;">Cricket Newsroom</h3>
          <div style="display:flex; gap:.4rem; align-items:center;">
            <button class="chip-btn" (click)="previousBanner()">Prev</button>
            <button class="chip-btn" (click)="nextBanner()">Next</button>
          </div>
        </div>

        <div class="news-tab-row" style="margin-top:.65rem;">
          <button
            *ngFor="let tab of newsTabs"
            class="chip-btn"
            [class.chip-active]="activeNewsTab === tab.key"
            (click)="setNewsTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>

        <div
          *ngIf="!newsLoading && headlineTags.length > 0"
          style="margin-top:.65rem; border:1px solid var(--border-subtle); border-radius:12px; padding:.55rem; background:rgba(255,255,255,.02);"
        >
          <div style="display:flex; align-items:center; gap:.5rem; flex-wrap:wrap;">
            <span class="text-secondary" style="font-size:.78rem; text-transform:uppercase; letter-spacing:.06em;">Trending Topics</span>
            <button
              *ngFor="let topic of headlineTags.slice(0, 9)"
              class="chip-btn"
              style="font-size:.72rem;"
              (click)="openByTopic(topic)"
            >
              {{ topic }}
            </button>
          </div>
        </div>

        <p *ngIf="newsLoading" class="text-secondary" style="margin-top:.75rem;">Loading stories...</p>

        <div class="news-layout" style="margin-top:.75rem;" *ngIf="!newsLoading && activeBanner as banner">
          <article class="news-banner news-lead">
            <img [src]="banner.image || fallbackNewsImage(banner)" [alt]="banner.title" class="lead-image" />
            <p class="news-kicker">Top Story</p>
            <p class="text-secondary" style="font-size:.78rem; margin:0;">{{ banner.source || 'News Desk' }} · {{ formatNewsTime(banner.timestamp) }}</p>
            <h3>{{ banner.title }}</h3>
            <p class="text-secondary" style="margin-top:.35rem;">{{ banner.summary }}</p>
            <div style="margin-top:.75rem; display:flex; gap:.55rem; flex-wrap:wrap;">
              <button class="btn btn-primary" (click)="openNewsModal(banner)">Details</button>
              <a routerLink="/analytics" class="btn btn-secondary">See Trends</a>
            </div>
          </article>

          <aside class="news-side">
            <div class="metric-box">
              <p class="metric-label">Live Pulse</p>
              <strong>{{ liveNowCount }}</strong>
              <p class="text-secondary" style="font-size:.76rem; margin-top:.25rem;">verified live matches right now</p>
            </div>
            <div class="metric-box">
              <p class="metric-label">Upcoming Radar</p>
              <strong>{{ upcomingMatches.length }}</strong>
              <p class="text-secondary" style="font-size:.76rem; margin-top:.25rem;">fixtures loaded for quick picks</p>
            </div>
            <div class="metric-box" *ngIf="newsCards.length > 0">
              <p class="metric-label">Coverage</p>
              <p class="text-secondary" style="font-size:.78rem; margin-top:.15rem;">{{ newsCards[0].title }}</p>
            </div>
            <div class="metric-box" *ngIf="newsCards.length > 1">
              <p class="metric-label">On This Day</p>
              <p class="text-secondary" style="font-size:.78rem; margin-top:.15rem;">{{ onThisDaySnippet }}</p>
            </div>

            <section class="most-read-box" *ngIf="mostReadNews.length > 0">
              <div class="most-read-head">
                <p class="metric-label" style="margin:0;">Most Read</p>
                <span class="text-secondary" style="font-size:.72rem;">Top {{ mostReadNews.length }}</span>
              </div>
              <button
                class="most-read-item"
                *ngFor="let story of mostReadNews; let i = index"
                (click)="openNewsModal(story)"
              >
                <span class="rank">{{ i + 1 }}</span>
                <span class="title">{{ story.title }}</span>
              </button>
            </section>
          </aside>
        </div>

        <div class="top-story-grid" *ngIf="!newsLoading && newsCards.length > 0">
          <div style="grid-column:1/-1; display:flex; justify-content:space-between; align-items:center; margin-bottom:.5rem;">
            <span class="text-secondary" style="font-size:.84rem;">{{ newsCards.length }} stories in {{ activeNewsTab }}</span>
          </div>
          <article class="top-story-item" *ngFor="let story of newsCards; let i = index" [style.animationDelay.ms]="i * 70">
            <img [src]="story.image || fallbackNewsImage(story)" [alt]="story.title" class="story-image" />
            <div style="display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.45rem .65rem 0;">
              <span class="news-pill">{{ story.category }}</span>
              <p class="text-secondary" style="font-size:.74rem; margin:0;">{{ formatNewsTime(story.timestamp) }}</p>
            </div>
            <h4>{{ story.title }}</h4>
            <p>{{ story.summary }}</p>
            <button class="btn btn-secondary" style="margin:.35rem .65rem .65rem;" (click)="openNewsModal(story)">Open Details</button>
          </article>
        </div>

        <p *ngIf="!newsLoading && !activeBanner" class="text-secondary" style="margin-top:.85rem;">No newsroom stories available right now.</p>
      </section>

      <section class="card" style="margin-bottom: 1rem;" *ngIf="isLoggedIn">
        <div style="display:flex; justify-content:space-between; gap:.75rem; align-items:center; flex-wrap:wrap;">
          <h3 style="margin:0;">Auto AI Predictions</h3>
          <span class="text-secondary">{{ predictionCards.length }} matches loaded</span>
        </div>

        <div class="home-grid" *ngIf="predictionCards.length > 0">
          <article class="prediction-card" *ngFor="let card of predictionCards">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:.55rem;">
              <strong>{{ card.match.team1?.name || 'Unknown' }} vs {{ card.match.team2?.name || 'Unknown' }}</strong>
              <span class="tag">{{ card.match.format | uppercase }}</span>
            </div>
            <p class="text-secondary" style="margin-top:.35rem;">{{ card.match.category }} · {{ card.match.status }}</p>

            <div *ngIf="!isLoggedIn" class="text-secondary" style="margin-top:.55rem;">
              Login to unlock AI prediction for this match.
            </div>
            <div *ngIf="isLoggedIn && card.loading" class="text-secondary" style="margin-top:.55rem;">Running prediction...</div>
            <div *ngIf="isLoggedIn && card.error" class="status-error" style="margin-top:.55rem;">{{ card.error }}</div>

            <div *ngIf="isLoggedIn && card.job?.result as result" style="margin-top:.55rem; display:grid; gap:.45rem;">
              <div>
                <div class="prob-row">
                  <span>{{ result.team1.name }}</span>
                  <strong>{{ (result.team1_win_probability * 100) | number:'1.0-1' }}%</strong>
                </div>
                <div class="prob-track">
                  <div class="prob-fill" [style.width.%]="result.team1_win_probability * 100"></div>
                </div>
              </div>
              <div>
                <div class="prob-row">
                  <span>{{ result.team2.name }}</span>
                  <strong>{{ (result.team2_win_probability * 100) | number:'1.0-1' }}%</strong>
                </div>
                <div class="prob-track">
                  <div class="prob-fill alt" [style.width.%]="result.team2_win_probability * 100"></div>
                </div>
              </div>
              <p class="text-secondary" style="font-size:.8rem; margin-top:.2rem;">
                Confidence {{ result.confidence_score | number:'1.2-2' }}
              </p>
            </div>

            <div style="margin-top:.7rem; display:flex; gap:.45rem; flex-wrap:wrap;">
              <a [routerLink]="['/matches', card.match.id]" class="btn btn-secondary">Match</a>
              <a *ngIf="isLoggedIn" [routerLink]="['/matches', card.match.id, 'predict']" class="btn btn-primary">AI Details</a>
              <a *ngIf="!isLoggedIn" routerLink="/auth/login" class="btn btn-primary">Login for AI</a>
            </div>
          </article>
        </div>

        <p *ngIf="predictionCards.length === 0" class="text-secondary" style="margin-top:.65rem;">
          No matches available for selected filters.
        </p>
      </section>

      <div class="grid" style="display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));">
        <section class="card" *ngIf="isLoggedIn || liveNowCount > 0">
          <h3>Live Match Strip</h3>
          <p *ngIf="!isLoggedIn && liveNowCount === 0" class="text-secondary" style="text-align:center; padding:1.5rem; background:var(--border-primary); border-radius:8px;">
            🔐 Login to track live matches and upcoming fixtures
          </p>
          <div *ngIf="isLoggedIn">
            <p *ngIf="liveError" class="status-error">{{ liveError }}</p>
            <p *ngIf="liveNowCount === 0 && upcomingMatches.length === 0" class="text-secondary">No live or upcoming matches right now.</p>
            <p *ngIf="liveNowCount === 0 && upcomingMatches.length > 0" class="text-secondary">No live matches right now. Showing upcoming fixtures.</p>
            <div *ngFor="let match of (liveNowCount > 0 ? verifiedLiveMatches : upcomingMatches).slice(0, 5)" class="list-row">
              <div style="display:flex; align-items:center; gap:.35rem; flex-wrap:wrap;">
                <strong>{{ match.team1?.name || 'Unknown' }}</strong>
                <span>vs</span>
                <strong>{{ match.team2?.name || 'Unknown' }}</strong>
              </div>
              <div class="text-secondary">
                {{ match.format | uppercase }} · {{ match.category }} · {{ liveNowCount > 0 ? 'live' : 'upcoming' }}
              </div>
            </div>
          </div>
        </section>

        <section class="card" *ngIf="isLoggedIn">
          <h3>Favorites Snapshot</h3>
          <p class="text-secondary" *ngIf="favouriteTeamNames.length === 0 && favouritePlayerNames.length === 0">
            Add favorites to personalize this section.
          </p>
          <p class="text-secondary" *ngIf="favouriteTeamNames.length > 0">
            Teams: {{ favouriteTeamNames.join(' · ') }}
          </p>
          <p class="text-secondary" *ngIf="favouritePlayerNames.length > 0">
            Players: {{ favouritePlayerNames.join(' · ') }}
          </p>
          <div style="margin-top:.75rem; display:flex; gap:.5rem; flex-wrap:wrap;">
            <a routerLink="/favorites" class="btn btn-primary">Open Favorites</a>
            <a routerLink="/auth/profile" class="btn btn-secondary">Edit Favorites</a>
          </div>
        </section>

        <section class="card" *ngIf="isAdmin">
          <h3>Pipeline Health</h3>
          <p *ngIf="loading" class="text-secondary">Loading status...</p>
          <p *ngIf="!loading && pipelineError" class="status-error">{{ pipelineError }}</p>
          <div *ngIf="!loading && pipelineStatus">
            <p><strong>Current matches:</strong> {{ pipelineStatus.count_current_matches }}</p>
            <p><strong>Live feed rows:</strong> {{ pipelineStatus.count_cricbuzz_live }}</p>
            <p><strong>Unified matches:</strong> {{ pipelineStatus.count_unified_matches }}</p>
            <p class="text-secondary">Last retraining: {{ pipelineStatus.last_model_retraining || 'N/A' }}</p>
          </div>
        </section>
      </div>

      <div style="margin-top:1rem; display:flex; gap:.75rem; flex-wrap:wrap;">
        <a routerLink="/matches" class="btn btn-primary">Browse Matches</a>
        <a *ngIf="isLoggedIn" routerLink="/predictions" class="btn btn-secondary">Predictions Hub</a>
        <a routerLink="/analytics" class="btn btn-secondary">Analytics</a>
        <a routerLink="/players" class="btn btn-secondary">Browse Players</a>
      </div>

      <div
        *ngIf="selectedNews as detail"
        style="position:fixed; inset:0; z-index:1200; background:rgba(3,10,18,.78); display:flex; align-items:center; justify-content:center; padding:1rem;"
        (click)="closeNewsModal()"
      >
        <article
          class="card"
          style="max-width:860px; width:min(100%, 860px); max-height:90vh; overflow:auto; border:1px solid rgba(94,234,212,.3); background:linear-gradient(165deg, rgba(9,16,28,.98), rgba(12,22,40,.98));"
          (click)="$event.stopPropagation()"
        >
          <div style="display:flex; justify-content:space-between; align-items:start; gap:.75rem;">
            <div>
              <p class="news-kicker" style="margin-bottom:.25rem;">{{ detail.category }}</p>
              <h2 style="margin:0; line-height:1.2;">{{ detail.title }}</h2>
              <p class="text-secondary" style="margin-top:.35rem; font-size:.82rem;" *ngIf="detail.source || detail.timestamp">
                {{ detail.source || 'News Desk' }}
                <span *ngIf="detail.timestamp"> · {{ detail.timestamp }}</span>
              </p>
            </div>
            <button class="btn btn-secondary" (click)="closeNewsModal()">Close</button>
          </div>

          <img *ngIf="detail.image" [src]="detail.image" [alt]="detail.title" style="width:100%; margin-top:.9rem; border-radius:12px; object-fit:cover; max-height:380px; border:1px solid var(--border-subtle);" />

          <p style="margin-top:.9rem; color:var(--text-secondary); line-height:1.55; font-size:.95rem;">
            {{ detail.summary }}
          </p>

          <div style="margin-top:1rem; display:flex; gap:.6rem; flex-wrap:wrap;">
            <a [routerLink]="detail.link" class="btn btn-primary" (click)="closeNewsModal()">Continue</a>
            <a routerLink="/matches" class="btn btn-secondary" (click)="closeNewsModal()">Related Matches</a>
          </div>
        </article>
      </div>
    </div>
  `,
  styles: [`
    .news-stage {
      background:
        radial-gradient(circle at 12% 20%, rgba(56, 189, 248, 0.08), transparent 38%),
        radial-gradient(circle at 88% 80%, rgba(16, 185, 129, 0.12), transparent 40%),
        linear-gradient(165deg, rgba(10, 16, 29, 0.95), rgba(12, 22, 40, 0.98));
      border: 1px solid rgba(80, 180, 255, 0.25);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.24);
    }

    .headline-ticker {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 0.6rem;
      border: 1px solid rgba(94, 234, 212, 0.25);
      border-radius: 12px;
      padding: 0.45rem 0.6rem;
      margin-bottom: 0.7rem;
      background: linear-gradient(90deg, rgba(13, 28, 44, 0.9), rgba(10, 18, 31, 0.96));
      cursor: pointer;
    }

    .ticker-label {
      text-transform: uppercase;
      font-size: 0.66rem;
      letter-spacing: 0.08em;
      color: #7fffe2;
      border: 1px solid rgba(127, 255, 226, 0.32);
      border-radius: 999px;
      padding: 0.13rem 0.45rem;
      background: rgba(20, 184, 166, 0.15);
      white-space: nowrap;
    }

    .ticker-track {
      overflow: hidden;
      position: relative;
      min-height: 1.2rem;
    }

    .ticker-text {
      display: inline-block;
      white-space: nowrap;
      color: var(--text-primary);
      font-size: 0.86rem;
      animation: tickerScroll 12s linear infinite;
    }

    .ticker-hint {
      color: var(--text-muted);
      font-size: 0.72rem;
      white-space: nowrap;
    }

    .hero-card {
      border: 1px solid var(--border-primary);
      background:
        radial-gradient(circle at top right, rgba(0, 212, 170, 0.18), transparent 45%),
        linear-gradient(160deg, rgba(15, 22, 35, 0.95), rgba(10, 15, 25, 0.92));
    }

    .hero-kicker {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }

    .quick-stats {
      margin-top: 1rem;
      display: grid;
      gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    }

    .quick-stat {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
      padding: 0.75rem;
      display: grid;
      gap: 0.15rem;
    }

    .quick-stat span {
      color: var(--text-muted);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .quick-stat strong {
      font-size: 1.28rem;
      color: var(--text-primary);
      font-family: var(--font-display);
    }

    .filter-row {
      margin-top: 0.95rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      align-items: center;
    }

    .chip-set {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    .chip-btn {
      border: 1px solid var(--border-muted);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.02);
      color: var(--text-secondary);
      padding: 0.28rem 0.7rem;
      cursor: pointer;
      text-transform: capitalize;
      font-size: 0.76rem;
    }

    .chip-btn.chip-active {
      border-color: var(--border-primary);
      color: var(--text-primary);
      background: rgba(0, 212, 170, 0.16);
    }

    .home-grid {
      margin-top: 0.9rem;
      display: grid;
      gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }

    .prediction-card {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.02);
      padding: 0.75rem;
    }

    .news-banner {
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-lg);
      background:
        radial-gradient(circle at right top, rgba(0, 212, 170, 0.2), transparent 45%),
        linear-gradient(135deg, rgba(9, 15, 26, 0.92), rgba(12, 20, 34, 0.95));
      padding: 1rem;
    }

    .news-layout {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 0.8rem;
    }

    .lead-image {
      width: 100%;
      height: 260px;
      object-fit: cover;
      border-radius: 14px;
      border: 1px solid rgba(255, 255, 255, 0.18);
      margin-bottom: 0.65rem;
      box-shadow: 0 14px 28px rgba(0, 0, 0, 0.35);
    }

    .news-lead h3 {
      font-size: 1.35rem;
      line-height: 1.2;
    }

    .news-side {
      display: grid;
      gap: 0.8rem;
    }

    .most-read-box {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 0.7rem;
      background: linear-gradient(145deg, rgba(15, 30, 52, 0.84), rgba(13, 26, 45, 0.9));
      display: grid;
      gap: 0.45rem;
    }

    .most-read-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
    }

    .most-read-item {
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.03);
      color: var(--text-primary);
      display: grid;
      grid-template-columns: 26px 1fr;
      align-items: center;
      gap: 0.5rem;
      padding: 0.45rem;
      text-align: left;
      cursor: pointer;
    }

    .most-read-item:hover {
      border-color: rgba(94, 234, 212, 0.45);
    }

    .most-read-item .rank {
      width: 24px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      font-size: 0.75rem;
      background: rgba(94, 234, 212, 0.14);
      color: #7fffe2;
      border: 1px solid rgba(94, 234, 212, 0.35);
    }

    .most-read-item .title {
      font-size: 0.78rem;
      line-height: 1.2;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .metric-box {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 0.9rem;
      background: linear-gradient(145deg, rgba(15, 30, 52, 0.84), rgba(13, 26, 45, 0.9));
    }

    .metric-box strong {
      font-family: var(--font-display);
      font-size: 2rem;
      color: #5eead4;
      line-height: 1;
    }

    .metric-label {
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }

    .top-story-grid {
      margin-top:.9rem;
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
      gap:1rem
    }

    .top-story-item {
      border:1px solid var(--border-subtle);
      border-radius:var(--radius-lg);
      padding:0;
      background:linear-gradient(180deg, rgba(17, 28, 48, 0.88), rgba(12, 20, 34, 0.95));
      overflow:hidden;
      display:flex;
      flex-direction:column;
      transition:transform .22s,border-color .22s, box-shadow .22s;
      box-shadow: 0 10px 22px rgba(0, 0, 0, 0.24);
      animation: storyRise .45s ease both;
    }

    .top-story-item:hover {
      transform:translateY(-6px);
      border-color:rgba(94,234,212,.6);
      box-shadow: 0 16px 30px rgba(0, 0, 0, 0.35);
    }

    .story-image {
      width:100%;
      height:210px;
      object-fit:cover;
      flex-shrink:0;
      filter: saturate(1.08) contrast(1.03);
    }

    .top-story-item h4 {
      font-size:.95rem;
      line-height:1.2;
      padding:.65rem .65rem .3rem
    }

    .top-story-item p {
      padding:0 .65rem;
      font-size:.84rem;
      line-height:1.35;
      margin:.45rem 0;
      display:-webkit-box;
      -webkit-line-clamp:3;
      -webkit-box-orient:vertical;
      overflow:hidden;
      color: var(--text-secondary);
    }

    .top-story-item a {
      padding:0 .65rem .65rem;
      margin-top:auto;
      color:#5eead4;
      font-size:.79rem;
      text-decoration:none
    }

    .news-pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(94, 234, 212, 0.35);
      background: rgba(94, 234, 212, 0.12);
      color: #7fffe2;
      border-radius: 999px;
      text-transform: capitalize;
      font-size: 0.66rem;
      letter-spacing: 0.05em;
      padding: 0.15rem 0.45rem;
    }

    @media (max-width: 920px) {
      .news-layout {
        grid-template-columns: 1fr;
      }

      .lead-image {
        height: 210px;
      }

      .story-image {
        height: 190px;
      }

      .headline-ticker {
        grid-template-columns: 1fr;
      }

      .ticker-text {
        animation-duration: 9s;
      }
    }

    @keyframes storyRise {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes tickerScroll {
      0% {
        transform: translateX(100%);
      }
      100% {
        transform: translateX(-100%);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .top-story-item,
      .ticker-text {
        animation: none !important;
      }
    }

    .news-kicker {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }

    .tag {
      border-radius: 999px;
      padding: 0.18rem 0.48rem;
      border: 1px solid var(--border-muted);
      font-size: 0.68rem;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .prob-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.78rem;
      margin-bottom: 0.2rem;
      color: var(--text-secondary);
    }

    .prob-track {
      height: 8px;
      border-radius: 99px;
      background: rgba(255, 255, 255, 0.08);
      overflow: hidden;
    }

    .prob-fill {
      height: 100%;
      border-radius: 99px;
      background: linear-gradient(90deg, #00d4aa 0%, #1dd9a0 100%);
    }

    .prob-fill.alt {
      background: linear-gradient(90deg, #22c55e 0%, #f59e0b 100%);
    }

  `],
})
export class DashboardComponent implements OnInit, OnDestroy {
  isLoggedIn = false;
  isAdmin = false;
  liveMatches: Match[] = [];
  upcomingMatches: Match[] = [];
  pipelineStatus: PipelineStatus | null = null;
  predictionCards: PredictionCard[] = [];
  favouriteTeamNames: string[] = [];
  favouritePlayerNames: string[] = [];
  formatFilter: MatchFormatFilter = 'all';
  categoryFilter: MatchCategoryFilter = 'all';
  readonly formatOptions: MatchFormatFilter[] = ['all', 't20', 'odi', 'test'];
  readonly categoryOptions: MatchCategoryFilter[] = ['all', 'international', 'franchise', 'domestic'];
  loading = true;
  pipelineError = '';
  liveError = '';
  private predictionPollers: number[] = [];
  newsLoading = false;
  activeNewsTab: NewsCategory = 'top';
  readonly newsTabs: Array<{ key: NewsCategory; label: string }> = [
    { key: 'top', label: 'Top Stories' },
    { key: 'trending', label: 'Trending' },
    { key: 'editorial', label: 'Editorial' },
    { key: 'rankings', label: 'Rankings' },
  ];
  newsBanners: NewsBanner[] = [
    {
      id: 1,
      title: 'AI Hub now prioritizes favorite-team fixtures first',
      summary: 'Home recommendations now score format affinity, team form, and upcoming recency for smarter picks.',
      linkLabel: 'Open Favorites',
      link: '/favorites',
      category: 'editorial',
      source: 'MatchMind',
    },
    {
      id: 2,
      title: 'Recent form trends available in Analytics',
      summary: 'Use team and player analytics to spot hot streaks before placing confidence in predictions.',
      linkLabel: 'Open Analytics',
      link: '/analytics',
      category: 'trending',
      source: 'MatchMind',
    },
    {
      id: 3,
      title: 'Create quick match predictions from AI Hub',
      summary: 'Select a live or upcoming fixture, run prediction in one click, and track confidence instantly.',
      linkLabel: 'Open AI Hub',
      link: '/predictions',
      category: 'top',
      source: 'MatchMind',
    },
  ];
  selectedNews: NewsBanner | null = null;
  tickerIndex = 0;
  activeBannerIndex = 0;
  private bannerIntervalId: number | null = null;
  private tickerIntervalId: number | null = null;

  constructor(private api: ApiService, private auth: AuthService) {}

  ngOnInit(): void {
    this.isLoggedIn = this.auth.isLoggedIn();
    this.isAdmin = this.auth.getCurrentUserRole() === 'ADMIN';

    this.bannerIntervalId = window.setInterval(() => this.nextBanner(), 6000);
    this.tickerIntervalId = window.setInterval(() => this.nextTicker(), 3600);

    // Load cricket news from API
    this.newsLoading = true;
    this.api.getCricketNews().subscribe({
      next: (response) => {
        const apiNews: NewsBanner[] = response.results.map((news: CricketNews) => ({
          id: Number(news.id || Date.now()),
          title: news.title,
          summary: news.summary || 'Latest cricket update from live feeds.',
          linkLabel: 'Read More',
          link: news.link && news.link.startsWith('/') ? news.link : '/matches',
          source: news.source,
          image: news.image,
          category: this.normalizeNewsCategory(news.category, news.title),
          timestamp: news.timestamp,
        }));

        if (apiNews.length > 0) {
          this.newsBanners = apiNews;
        }
        this.newsLoading = false;
      },
      error: () => {
        // Keep default banners if API fails.
        this.newsLoading = false;
      },
    });

    if (this.isLoggedIn) {
      this.auth.loadProfile().subscribe({
        next: (profile) => {
          this.favouriteTeamNames = (profile.favourite_teams || []).map((team) => team.name);
          this.favouritePlayerNames = (profile.favourite_players || []).slice(0, 6).map((player) => player.name);
        },
        error: () => {
          this.favouriteTeamNames = [];
          this.favouritePlayerNames = [];
        },
      });
    }

    this.api.getLiveMatches().subscribe({
      next: (response) => {
        this.liveMatches = response.results || [];
        this.liveError = '';
        this.tryBuildPredictionCards();
      },
      error: () => {
        this.liveMatches = [];
        this.liveError = 'Live matches could not be loaded.';
      },
    });

    this.api.getMatches({ status: 'upcoming' }).subscribe({
      next: (response) => {
        this.upcomingMatches = response.results;
        this.tryBuildPredictionCards();
      },
      error: () => {
        this.upcomingMatches = [];
      },
    });

    if (this.isAdmin) {
      this.api.getPipelineStatus().subscribe({
        next: (status) => {
          this.pipelineStatus = status;
          this.loading = false;
          this.pipelineError = '';
        },
        error: () => {
          this.loading = false;
          this.pipelineError = 'Pipeline status is currently unavailable.';
        },
      });
    } else {
      this.loading = false;
    }
  }

  ngOnDestroy(): void {
    this.clearPredictionPollers();
    if (this.bannerIntervalId !== null) {
      window.clearInterval(this.bannerIntervalId);
      this.bannerIntervalId = null;
    }
    if (this.tickerIntervalId !== null) {
      window.clearInterval(this.tickerIntervalId);
      this.tickerIntervalId = null;
    }
  }

  get activeBanner(): NewsBanner | null {
    const pool = this.filteredNews;
    if (pool.length === 0) {
      return null;
    }
    const index = this.normalizedBannerIndex(pool.length);
    return pool[index];
  }

  get filteredNews(): NewsBanner[] {
    const scoped = this.newsBanners.filter((item) => item.category === this.activeNewsTab);
    return scoped.length > 0 ? scoped : this.newsBanners;
  }

  get newsCards(): NewsBanner[] {
    const pool = this.filteredNews;
    if (pool.length <= 1) {
      return [];
    }
    const activeIndex = this.normalizedBannerIndex(pool.length);
    return pool.filter((_, index) => index !== activeIndex);
  }

  get mostReadNews(): NewsBanner[] {
    return [...this.filteredNews]
      .sort((a, b) => (b.title?.length || 0) - (a.title?.length || 0))
      .slice(0, 5);
  }

  get currentTickerHeadline(): NewsBanner | null {
    const pool = this.filteredNews;
    if (pool.length === 0) {
      return null;
    }
    const index = ((this.tickerIndex % pool.length) + pool.length) % pool.length;
    return pool[index];
  }

  get headlineTags(): string[] {
    const words = this.filteredNews
      .flatMap((story) => (story.title || '').split(/[^A-Za-z0-9]+/))
      .map((word) => word.trim())
      .filter((word) => word.length >= 5);

    const stopWords = new Set(['about', 'after', 'their', 'there', 'which', 'where', 'would', 'could', 'against', 'under', 'while', 'being']);
    const counts = new Map<string, number>();

    for (const rawWord of words) {
      const lower = rawWord.toLowerCase();
      if (stopWords.has(lower)) {
        continue;
      }
      counts.set(rawWord, (counts.get(rawWord) || 0) + 1);
    }

    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([word]) => word);
  }

  get onThisDaySnippet(): string {
    const source = this.newsCards[this.newsCards.length - 1] || this.activeBanner;
    if (!source) {
      return 'Historic cricket moments and major match milestones.';
    }
    return source.title;
  }

  openByTopic(topic: string): void {
    const found = this.filteredNews.find((story) => (story.title || '').toLowerCase().includes(topic.toLowerCase()));
    if (found) {
      this.openNewsModal(found);
    }
  }

  formatNewsTime(rawTimestamp?: string): string {
    if (!rawTimestamp) {
      return 'Just now';
    }

    const numericTs = Number(rawTimestamp);
    const date = Number.isFinite(numericTs) && numericTs > 0
      ? new Date(numericTs)
      : new Date(rawTimestamp);

    if (Number.isNaN(date.getTime())) {
      return 'Recent';
    }

    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  fallbackNewsImage(story: NewsBanner): string {
    const category = (story.category || 'top').toLowerCase();
    const safeTitle = (story.title || 'Cricket Update').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    const palette = category === 'trending'
      ? { a: '#fb923c', b: '#ef4444' }
      : category === 'editorial'
      ? { a: '#38bdf8', b: '#2563eb' }
      : category === 'rankings'
      ? { a: '#22c55e', b: '#0ea5a4' }
      : { a: '#14b8a6', b: '#0f766e' };

    const svg = `
      <svg xmlns='http://www.w3.org/2000/svg' width='1200' height='675' viewBox='0 0 1200 675'>
        <defs>
          <linearGradient id='g' x1='0%' y1='0%' x2='100%' y2='100%'>
            <stop offset='0%' stop-color='${palette.a}'/>
            <stop offset='100%' stop-color='${palette.b}'/>
          </linearGradient>
        </defs>
        <rect width='1200' height='675' fill='url(#g)'/>
        <circle cx='1060' cy='-40' r='220' fill='rgba(255,255,255,0.12)'/>
        <circle cx='120' cy='690' r='240' fill='rgba(0,0,0,0.18)'/>
        <text x='60' y='110' fill='rgba(255,255,255,0.92)' font-family='Segoe UI, Arial' font-size='34' font-weight='700'>MATCHMIND NEWS</text>
        <text x='60' y='165' fill='rgba(255,255,255,0.84)' font-family='Segoe UI, Arial' font-size='22'>${safeTitle.slice(0, 84)}</text>
      </svg>
    `;

    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  openNewsModal(story: NewsBanner): void {
    this.selectedNews = story;
  }

  closeNewsModal(): void {
    this.selectedNews = null;
  }

  openTickerStory(): void {
    if (this.currentTickerHeadline) {
      this.openNewsModal(this.currentTickerHeadline);
    }
  }

  get verifiedLiveMatches(): Match[] {
    return this.liveMatches.filter((match) => this.isMatchLiveNow(match));
  }

  get liveNowCount(): number {
    return this.verifiedLiveMatches.length;
  }

  nextBanner(): void {
    const pool = this.filteredNews;
    if (pool.length === 0) {
      return;
    }
    this.activeBannerIndex = (this.activeBannerIndex + 1) % pool.length;
  }

  previousBanner(): void {
    const pool = this.filteredNews;
    if (pool.length === 0) {
      return;
    }
    this.activeBannerIndex = (this.activeBannerIndex - 1 + pool.length) % pool.length;
  }

  setNewsTab(tab: NewsCategory): void {
    if (this.activeNewsTab === tab) {
      return;
    }
    this.activeNewsTab = tab;
    this.activeBannerIndex = 0;
    this.tickerIndex = 0;
  }

  nextTicker(): void {
    const pool = this.filteredNews;
    if (pool.length === 0) {
      return;
    }
    this.tickerIndex = (this.tickerIndex + 1) % pool.length;
  }

  setFormatFilter(value: MatchFormatFilter): void {
    this.formatFilter = value;
    this.refreshAutoPredictions();
  }

  setCategoryFilter(value: MatchCategoryFilter): void {
    this.categoryFilter = value;
    this.refreshAutoPredictions();
  }

  refreshAutoPredictions(): void {
    this.clearPredictionPollers();
    this.tryBuildPredictionCards();
  }

  private tryBuildPredictionCards(): void {
    const candidateMatches = [...this.verifiedLiveMatches, ...this.upcomingMatches]
      .filter((match) => this.matchPassesFilters(match))
      .slice(0, 8);

    this.predictionCards = candidateMatches.map((match) => ({
      match,
      loading: true,
      error: '',
      job: null,
    }));

    if (!this.isLoggedIn) {
      this.predictionCards = this.predictionCards.map((card) => ({ ...card, loading: false }));
      return;
    }

    this.predictionCards.forEach((card) => this.resolvePrediction(card));
  }

  private matchPassesFilters(match: Match): boolean {
    const format = (match.format || '').toLowerCase();
    const category = (match.category || '').toLowerCase();
    const formatAllowed = this.formatFilter === 'all' || format === this.formatFilter;
    const categoryAllowed = this.categoryFilter === 'all' || category === this.categoryFilter;
    return formatAllowed && categoryAllowed;
  }

  private resolvePrediction(card: PredictionCard): void {
    this.api.getLatestPredictionForMatch(card.match.id, 'pre_match').subscribe({
      next: (job) => {
        card.job = job;
        card.loading = false;
        if (job.status === 'pending' || job.status === 'processing') {
          this.schedulePredictionRefresh(card, job.id, 1);
        }
      },
      error: () => {
        this.api.createPrediction(card.match.id, 'pre_match').subscribe({
          next: (job) => {
            card.job = job;
            card.loading = false;
            if (job.status === 'pending' || job.status === 'processing') {
              this.schedulePredictionRefresh(card, job.id, 1);
            }
          },
          error: () => {
            card.loading = false;
            card.error = 'Prediction unavailable right now.';
          },
        });
      },
    });
  }

  private schedulePredictionRefresh(card: PredictionCard, jobId: number, attempt: number): void {
    if (attempt > 4) {
      return;
    }

    const timer = window.setTimeout(() => {
      this.api.getPrediction(jobId).subscribe({
        next: (job) => {
          card.job = job;
          if (job.status === 'pending' || job.status === 'processing') {
            this.schedulePredictionRefresh(card, jobId, attempt + 1);
          }
        },
      });
    }, 1800);

    this.predictionPollers.push(timer);
  }

  private clearPredictionPollers(): void {
    this.predictionPollers.forEach((timer) => window.clearTimeout(timer));
    this.predictionPollers = [];
  }

  private normalizedBannerIndex(poolLength: number): number {
    if (poolLength <= 0) {
      return 0;
    }
    return ((this.activeBannerIndex % poolLength) + poolLength) % poolLength;
  }

  private normalizeNewsCategory(rawCategory: string | undefined, title: string): NewsCategory {
    const candidate = (rawCategory || '').toLowerCase();
    if (candidate === 'top' || candidate === 'trending' || candidate === 'editorial' || candidate === 'rankings') {
      return candidate;
    }

    const loweredTitle = (title || '').toLowerCase();
    if (loweredTitle.includes('rank')) return 'rankings';
    if (loweredTitle.includes('analysis') || loweredTitle.includes('preview') || loweredTitle.includes('opinion')) return 'editorial';
    if (loweredTitle.includes('trend') || loweredTitle.includes('hot') || loweredTitle.includes('viral')) return 'trending';
    return 'top';
  }

  private isMatchLiveNow(match: Match): boolean {
    if ((match.status || '').toLowerCase() !== 'live') {
      return false;
    }

    const now = new Date();
    if (match.match_datetime) {
      const start = new Date(match.match_datetime);
      if (!Number.isNaN(start.getTime())) {
        const diffHours = (now.getTime() - start.getTime()) / (1000 * 60 * 60);
        return diffHours >= -1.5 && diffHours <= 16;
      }
    }

    if (match.match_date) {
      const todayIso = now.toISOString().slice(0, 10);
      return match.match_date === todayIso;
    }

    return false;
  }
}
