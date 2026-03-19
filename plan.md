# 🏏 Cricket Analytics & Prediction Platform — Development Plan

> **Status:** Phase 0 Complete — API integration tested, data flowing  
> **Stack:** Angular 17 · Django 5 · PostgreSQL 16 · Redis · Celery · Docker · scikit-learn / XGBoost / TensorFlow  
> **Goal:** 86%+ match prediction accuracy, 5,000+ users, 99.5% uptime

---

## 📦 Repository Structure (Target)

```
prediction_analytics-Platform/
├── resources/                        ← ALL reference material lives here
│   ├── docs/
│   │   ├── DPR - Multi-Sport Analytics & Prediction Platform.docx
│   │   ├── Cricket API Endpoints for Prediction.docx
│   │   ├── Diagrams - Multi-Sport Analytics & Prediction Platform.docx
│   │   └── Tech Stack Installation.docx
│   ├── diagrams/                     ← Architecture PNGs
│   │   ├── System Architecture.png
│   │   ├── AIML Prediction Process.png
│   │   ├── Data Flow & ETL Process.png
│   │   ├── Deployment & DevOps Pipeline.png
│   │   ├── End-to-End Application Workflow.png
│   │   ├── Hybrid Data Collection Strategy.png
│   │   └── User Management & Security Architecture.png
│   ├── prototypes/
│   │   └── api_testing_web/          ← Working static cricket dashboard (KEEP AS-IS)
│   ├── notes/
│   │   ├── get_start.txt
│   │   └── hacks.txt
│   └── components/
│       └── cricket_dpr_doc.tsx       ← React DPR viewer component
├── backend/                          ← Django + DRF
├── frontend/                         ← Angular 17
├── ml/                               ← AI/ML models & notebooks
├── infra/                            ← Docker, Nginx, CI/CD configs
├── plan.md                           ← This file
└── README.md
```

---

## 🗂️ Phase Overview

| Phase | Name | Duration | Goal |
|-------|------|----------|------|
| 0 | **Foundation & Setup** | Week 1–2 | Repo structure, Docker, DB schema, CI/CD skeleton |
| 1 | **Data Pipeline** | Week 3–5 | ETL from CricAPI + Cricbuzz → PostgreSQL, Celery jobs |
| 2 | **Backend API** | Week 6–8 | Django REST endpoints for matches, players, series, predictions |
| 3 | **ML Core** | Week 9–13 | Feature engineering + model training (pre-match) |
| 4 | **Frontend** | Week 14–17 | Angular SPA with dashboard, predictions, analytics |
| 5 | **Live Prediction** | Week 18–20 | Real-time in-match prediction (run rate, wickets) |
| 6 | **DevOps & Monitoring** | Week 21–22 | Production Docker Compose, Prometheus, Grafana |
| 7 | **Polish & Launch** | Week 23–26 | Auth, user profiles, performance tuning, soft launch |

---

## 📋 Phase 0 — Foundation & Repository Setup (Week 1–2)

### 0.1 Move Resources
- [ ] Create `resources/` folder with `docs/`, `diagrams/`, `prototypes/`, `notes/`, `components/` subdirectories
- [ ] Move all `.docx` files → `resources/docs/`
- [ ] Move `Diagrams/` folder → `resources/diagrams/`
- [ ] Move `api_testing_web/` → `resources/prototypes/api_testing_web/`
- [ ] Move `get_start.txt` + `hacks.txt` → `resources/notes/`
- [ ] Move `cricket_dpr_doc.tsx` → `resources/components/`
- [ ] Delete `api_testing_web.zip` (already extracted)
- [ ] Delete temp lock files `~$*.docx`

### 0.2 Initialize Backend (Django)
```
backend/
├── manage.py
├── requirements.txt
├── config/              ← settings (base, dev, prod)
├── apps/
│   ├── core/            ← shared utils, middleware
│   ├── accounts/        ← User auth + JWT
│   ├── matches/         ← Match data models + APIs
│   ├── players/         ← Player models + APIs
│   ├── series/          ← Series models + APIs
│   ├── predictions/     ← Prediction request/response APIs
│   └── analytics/       ← Stats, dashboards, charts APIs
└── ml_engine/           ← ML model loading + inference
```

**Key Django apps to scaffold:**
- `accounts` — custom User model, JWT auth (djangorestframework-simplejwt)
- `matches` — Match, Team, Venue models
- `players` — Player, PlayerStats models
- `predictions` — Prediction, PredictionResult models
- `data_pipeline` — API ingestion management commands + Celery tasks

### 0.3 Initialize Frontend (Angular 17)
```
frontend/
├── src/app/
│   ├── core/            ← guards, interceptors, services
│   ├── shared/          ← components, pipes, directives
│   ├── features/
│   │   ├── dashboard/
│   │   ├── matches/
│   │   ├── players/
│   │   ├── series/
│   │   ├── predictions/
│   │   └── analytics/
│   └── layout/          ← navbar, sidebar, footer
```

### 0.4 Docker Compose (Dev)
```yaml
services:
  db:          # PostgreSQL 16
  redis:       # Redis 7
  backend:     # Django + Gunicorn
  celery:      # Celery worker
  celery-beat: # Celery beat (scheduled tasks)
  frontend:    # Angular dev server / Nginx
```

### 0.5 Database Schema (Initial)
```sql
-- Core tables
teams, venues, series, players
matches (id, team1, team2, format, date, venue, status, result)
match_scorecards (match_id, innings, batting_stats, bowling_stats)
player_stats (player_id, match_id, runs, wickets, sr, economy)

-- Prediction tables
prediction_jobs (match_id, requested_at, model_version, status)
prediction_results (job_id, team1_win_prob, team2_win_prob, confidence, features_snapshot)

-- User tables
users (id, email, username, created_at)
user_predictions (user_id, prediction_id, viewed_at)
```

---

## 📋 Phase 1 — Data Pipeline (Week 3–5)

### 1.1 Data Sources (Already Proven in `api_testing_web`)
| Source | Endpoint | Used For | Rate Limit |
|--------|----------|----------|------------|
| CricAPI (`api.cricapi.com`) | `/currentMatches`, `/matches`, `/players`, `/series_info` | Live matches, players | 100/day (free) |
| Cricbuzz via RapidAPI | `/matches/v1/recent`, `/matches/v1/live` | Live + recent results | 500/month (free) |

### 1.2 Django Management Commands
- `python manage.py sync_current_matches` — pull active matches → DB
- `python manage.py sync_series` — pull series data
- `python manage.py sync_player_stats --match-id=<id>` — pull match scorecard

### 1.3 Celery Scheduled Tasks
```python
# Every 5 minutes: sync live match data
# Every 1 hour: sync completed match results
# Every 6 hours: sync player stats
# Every day at midnight: run model re-training pipeline
```

### 1.4 Data Normalization
- Port logic from `api_testing_web/app/domain/normalize.js` to Python (`data_pipeline/normalizers.py`)
- Deduplicate matches across CricAPI + Cricbuzz using name similarity
- Standardize: team names, player names, venue names, format (test/odi/t20/t10)

### 1.5 Redis Caching Strategy
- Cache live match data: TTL 60s
- Cache completed matches: TTL 6h
- Cache player stats: TTL 24h
- Cache prediction results: TTL 30min (until match starts)

---

## 📋 Phase 2 — Backend REST API (Week 6–8)

### 2.1 Endpoints

```
# Matches
GET  /api/v1/matches/               → list (filters: status, format, date, category)
GET  /api/v1/matches/{id}/          → detail + scorecard
GET  /api/v1/matches/live/          → live matches only

# Series
GET  /api/v1/series/                → list
GET  /api/v1/series/{id}/matches/   → matches in series

# Players
GET  /api/v1/players/               → search (name, team)
GET  /api/v1/players/{id}/          → profile + recent stats

# Predictions
POST /api/v1/predictions/           → trigger prediction for match
GET  /api/v1/predictions/{id}/      → result (win prob, confidence, features)
GET  /api/v1/predictions/match/{match_id}/ → latest prediction for a match

# Analytics
GET  /api/v1/analytics/team/{team_name}/   → team stats
GET  /api/v1/analytics/player/{id}/        → player career trends

# Auth
POST /api/v1/auth/register/
POST /api/v1/auth/login/            → returns JWT
POST /api/v1/auth/refresh/
```

### 2.2 Performance Requirements
- All list endpoints < 200ms (Redis caching)
- Prediction endpoint: async task (Celery), poll for result
- Rate limiting: 100 req/min per IP, 1000 req/min authenticated

---

## 📋 Phase 3 — ML Core (Week 9–13)

### 3.1 Pre-Match Prediction Features
Based on `hacks.txt` notes:

| Feature Group | Features |
|---------------|---------|
| **Team Form** | Win rate last 10 matches, head-to-head record, home/away record |
| **Player Form** | Top 5 batsmen avg last 5 innings, top 3 bowlers economy last 5 |
| **Venue** | Venue average score, pitch behavior (batting/bowling friendly) |
| **Format** | Match format encoding (Test=0.25, ODI=0.5, T20=0.75, T10=1.0) |
| **Context** | Tournament stage, team rankings (ICC), match importance |

### 3.2 In-Match (Live) Prediction Features
Based on `hacks.txt`:
- Run rate gap (RRR - CRR)
- Wickets fallen vs wickets in hand
- Over-by-over momentum score
- Partnership analysis

### 3.3 Model Architecture (Ensemble)
```
Pre-match Model:
  ├── Random Forest     (30%) → handles non-linear patterns
  ├── XGBoost          (35%) → handles imbalanced data
  ├── Neural Network   (25%) → deep pattern recognition (2 hidden layers)
  └── Meta Learner     (10%) → stacking/blending

Live Model:
  └── LSTM sequence model → time-series over-by-over data
```

### 3.4 ML Folder Structure
```
ml/
├── notebooks/
│   ├── 01_eda.ipynb              ← Exploratory Data Analysis
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_model_evaluation.ipynb
├── src/
│   ├── features/
│   │   ├── pre_match.py          ← pre-match feature builder
│   │   └── live_match.py         ← live feature builder
│   ├── models/
│   │   ├── ensemble.py           ← ensemble predictor
│   │   ├── train.py              ← training script
│   │   └── evaluate.py           ← accuracy, calibration metrics
│   └── utils/
│       ├── data_loader.py        ← load from PostgreSQL
│       └── preprocessor.py       ← encoding, scaling, imputation
├── artifacts/                    ← saved model files (.pkl, .pt)
└── requirements-ml.txt
```

### 3.5 Model Evaluation Targets
- **Accuracy:** ≥ 86% (pre-match)
- **Calibration:** Brier Score < 0.2
- **AUC-ROC:** ≥ 0.90
- **Live prediction update latency:** < 2 seconds

---

## 📋 Phase 4 — Angular Frontend (Week 14–17)

### 4.1 Pages & Screens
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Dashboard | Live matches, quick stats, trending |
| `/matches` | MatchList | Filters: format, status, category, date |
| `/matches/:id` | MatchDetail | Scorecard + live updates |
| `/matches/:id/predict` | PredictionView | Win probability gauge, factors |
| `/series` | SeriesList | Browse ongoing/upcoming series |
| `/series/:id` | SeriesDetail | Matches within series |
| `/players` | PlayerSearch | Search by name/team |
| `/players/:id` | PlayerProfile | Stats, form, prediction impact |
| `/analytics` | AnalyticsDashboard | Charts, trends, comparisons |
| `/auth/login` | Login | JWT auth |
| `/auth/register` | Register | Sign up |

### 4.2 UI Design Principles
- **Dark mode first** — sports analytics feel (dark navy/charcoal + accent colors)
- **Real-time feel** — WebSocket or polling for live updates
- **Data-dense but clear** — inspired by ESPN CricInfo / Cricbuzz
- Charts: Chart.js or ngx-charts
- Icons: Lucide / Material Icons

### 4.3 Key Angular Services
- `MatchService` — CRUD + polling for live matches
- `PredictionService` — trigger + poll prediction jobs
- `PlayerService` — player search + profile
- `AuthService` — JWT login/refresh with interceptors
- `WebSocketService` — optional real-time score updates

---

## 📋 Phase 5 — Live Prediction Engine (Week 18–20)

- Celery task: triggered every over (6 balls) for live matches
- WebSocket endpoint (Django Channels) → push updated probabilities to Angular
- Use Cricbuzz RapidAPI live data as primary source
- Fallback to CricAPI if Cricbuzz rate-limited
- Display: animated probability bar updating over-by-over

---

## 📋 Phase 6 — DevOps & Monitoring (Week 21–22)

### 6.1 Docker Compose (Production)
```
services: db, redis, backend, celery, celery-beat, nginx, prometheus, grafana
```

### 6.2 Nginx Configuration
- Reverse proxy: `/api/` → Django, `/` → Angular static build
- SSL termination (Let's Encrypt)
- Gzip compression

### 6.3 Monitoring Stack
- **Prometheus** — collect metrics from Django (django-prometheus)
- **Grafana** — dashboards for: API latency, Celery task queue depth, DB connections, ML prediction times
- **Alerts:** Celery queue depth > 100, API error rate > 1%, DB connections > 80%

### 6.4 CI/CD Pipeline (GitHub Actions)
```yaml
on: [push to main]
jobs:
  test:    → pytest (backend) + ng test (frontend)
  lint:    → flake8 + eslint
  build:   → docker build & push to registry
  deploy:  → docker compose pull && up -d
```

---

## 📋 Phase 7 — Polish & Launch (Week 23–26)

- [ ] User accounts: save favourite teams, prediction history
- [ ] Email notifications: match start alerts, prediction ready
- [ ] API key rotation: environment-based config (not hardcoded)
- [ ] Performance audit: Lighthouse score ≥ 90
- [ ] Security audit: OWASP checks, dependency vulnerability scan
- [ ] SEO: meta tags, og:image, schema markup for match pages
- [ ] Soft launch: deploy to VPS (DigitalOcean / Hetzner), invite beta users
- [ ] Collect feedback, iterate on model accuracy

---

## 🔑 API Keys (Current — Move to `.env`)

> ⚠️ These are in `resources/prototypes/api_testing_web/app/config.js` — never commit to git!

```env
CRICAPI_KEY=3e7324ce-b3a3-48f6-9591-5164b38f51db
CRICBUZZ_RAPIDAPI_KEY=99c4a70c66msh1afc8d1d442246dp105f9djsn9bb49a4b889c
CRICBUZZ_RAPIDAPI_HOST=cricbuzz-cricket2.p.rapidapi.com
```

Add to `backend/.env` and `frontend/src/environments/` — never hardcode.

---

## 🎯 Immediate Next Steps (Start Today)

1. **Move resources** → create `resources/` folder structure, move all docs/diagrams/prototypes
2. **Scaffold `backend/`** → `django-admin startproject config .` inside `backend/`
3. **Scaffold `frontend/`** → `ng new frontend --standalone --routing --style=scss`
4. **Write `docker-compose.dev.yml`** → db, redis, backend, frontend services
5. **Create `.env.example`** → document all required env vars
6. **Initialize `ml/`** → folder structure + `requirements-ml.txt`
7. **Port normalization logic** → `api_testing_web/domain/normalize.js` → Python

---

## 📊 Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Pre-match accuracy | ≥ 86% | Backtesting on 2020–2024 matches |
| API response time | < 200ms | Prometheus p95 latency |
| System uptime | ≥ 99.5% | Grafana uptime dashboard |
| Data freshness | < 5 min lag | Celery task monitoring |
| Frontend load time | < 3s | Lighthouse performance score |

---

*Plan Version: 1.0 | Date: March 2026 | Author: Dev Team*
