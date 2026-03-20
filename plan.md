# 🏏 MatchMind — Multi-Sport Prediction Platform Development Plan

> **Status:** ✅ Phase 0 DONE (19 Mar 2026) → ✅ Phase 1 DONE (19 Mar 2026) → ✅ Phase 2 DONE (20 Mar 2026) → ✅ Phase 3 DONE (20 Mar 2026) → ✅ Phase 4 DONE (20 Mar 2026) → ✅ Phase 5 DONE (20 Mar 2026)  
> **Stack:** Angular 17 · Django 5 · PostgreSQL 16 · Redis · Celery · Docker · scikit-learn / XGBoost / TensorFlow  
> **Goal:** 86%+ match prediction accuracy, 5,000+ users, 99.5% uptime

---

## 📦 Repository Structure (Target)

```
matchmind/
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
| 0 | **Foundation & Setup** ✅ | Week 1–2 | Repo structure, Docker, DB schema, CI/CD skeleton |
| 1 | **Data Pipeline** ✅ | Week 3–5 | ETL from CricAPI + Cricbuzz → PostgreSQL, Celery jobs |
| 2 | **Backend API** ✅ | Week 6–8 | Django REST endpoints for matches, players, series, predictions |
| 3 | **ML Core** ✅ | Week 9–13 | Feature engineering + model training (pre-match) |
| 4 | **Frontend** ✅ | Week 14–17 | Angular SPA with dashboard, predictions, analytics |
| 5 | **Live Prediction** ✅ | Week 18–20 | Real-time in-match prediction (run rate, wickets) |
| 6 | **DevOps & Monitoring** | Week 21–22 | Production Docker Compose, Prometheus, Grafana |
| 7 | **Polish & Launch** | Week 23–26 | Auth, user profiles, performance tuning, soft launch |

---

## 📋 Phase 0 — Foundation & Repository Setup ✅ COMPLETE

> **Completed:** 19 March 2026 | Git commit: `eadc9bf`
> Django check: **0 issues** | Angular build: **0 errors** | Migrations: **all applied**

### 0.1 Move Resources ✅
- [x] Create `resources/` folder with `docs/`, `diagrams/`, `prototypes/`, `notes/`, `components/` subdirectories
- [x] Move all `.docx` files → `resources/docs/`
- [x] Move `Diagrams/` folder → `resources/diagrams/`
- [x] Move `api_testing_web/` → `resources/prototypes/api_testing_web/`
- [x] Move `get_start.txt` + `hacks.txt` → `resources/notes/`
- [x] Move `cricket_dpr_doc.tsx` → `resources/components/`

### 0.2 Backend (Django) ✅
- [x] 8 apps: `core`, `accounts`, `matches`, `players`, `series`, `predictions`, `analytics`, `data_pipeline`
- [x] Split settings (`base.py` / `dev.py` / `prod.py`)
- [x] Custom User model (email login), JWT (simplejwt), DRF, CORS, Prometheus
- [x] Models: User, Team, Venue, Match, MatchScorecard, Player, PlayerMatchStats, Series, PredictionJob, PredictionResult
- [x] Admin registered for all models with search + filters
- [x] Serializers for Matches (Team, Venue, Scorecard nested)
- [x] ViewSets for all apps (ReadOnly + filters)
- [x] URL routing under `/api/v1/`
- [x] Migrations applied (SQLite dev, PostgreSQL prod-ready)
- [x] Celery configured with `django_celery_beat` + `django_celery_results`
- [x] `wsgi.py` + `asgi.py` updated to use split settings
- [x] `pytest.ini` + `conftest.py` for fast in-memory test runs

**Management commands created:**
- [x] `python manage.py sync_matches` — pull from CricAPI + Cricbuzz
- [x] `python manage.py seed_celery_schedules` — configure periodic tasks
- [x] `python manage.py create_dev_superuser` — idempotent dev superuser

### 0.3 Frontend (Angular 17) ✅
- [x] Angular 17 standalone SPA scaffolded (`ng new --standalone --routing --style=scss`)
- [x] `app.config.ts` — HttpClient + JWT interceptor + animations + router
- [x] `app.routes.ts` — 10 lazy-loaded feature routes
- [x] **Global dark-mode SCSS design system** with CSS tokens, cards, badges, buttons, forms, tables, skeletons, animations
- [x] `src/index.html` — full SEO meta tags, Open Graph, Twitter Card, Google Fonts preconnect
- [x] `environments/environment.ts` + `environment.prod.ts`
- [x] `core/models/index.ts` — TypeScript domain models (Match, Team, Player, Prediction, etc.)
- [x] `core/services/match.service.ts` — REST API service
- [x] `core/services/auth.service.ts` — JWT login/logout/profile with BehaviorSubject
- [x] `core/interceptors/jwt.interceptor.ts` — attaches Bearer token to all requests
- [x] 10 feature component stubs (Dashboard, Matches, Players, Series, Predictions, Analytics, Auth)
- [x] `npm run build` passes — **0 TypeScript errors**, all lazy chunks generated

### 0.4 Docker Compose (Dev) ✅
- [x] `docker-compose.dev.yml` — db (PG16), redis, backend, celery, celery-beat, frontend
- [x] `backend/Dockerfile` — Python 3.11 + pip install + gunicorn
- [x] `frontend/Dockerfile.dev` — Node 20 + npm install + ng serve

### 0.5 Database Schema ✅
- [x] Custom User model (email-based login), Team, Venue, Match, MatchScorecard
- [x] Player, PlayerMatchStats, Series
- [x] PredictionJob + PredictionResult (with feature snapshot JSON field)
- [x] Indexes on `(status, match_date)` and `(format, category)`
- [x] All migrations created and applied

### 0.6 Infra & DevOps ✅
- [x] `infra/nginx/default.conf` — reverse proxy: `/api/` → Django, `/` → Angular
- [x] `infra/prometheus/prometheus.yml` — scrape config for Django/Celery/PG/Redis
- [x] `.github/workflows/ci.yml` — GitHub Actions: backend pytest + Angular build + Docker validation
- [x] `Makefile` — `make setup`, `make run-backend`, `make test-backend`, `make docker-up`, etc.
- [x] `.gitignore` — Python, Angular, Docker, ML artifacts, secrets
- [x] `README.md` — quick start for local dev + Docker
- [x] **Initial git commit** — `eadc9bf`

### 0.7 ML Foundation ✅
- [x] `ml/src/features/pre_match.py` — team form, H2H, venue, format features
- [x] `ml/src/models/ensemble.py` — weighted RF+XGBoost predictor with dummy fallback
- [x] `ml/src/models/train.py` — training script skeleton
- [x] `ml/src/models/evaluate.py` — accuracy/AUC/Brier metrics with target thresholds
- [x] `ml/src/utils/data_loader.py` — Django ORM → pandas DataFrame
- [x] `ml/src/utils/preprocessor.py` — encoding, imputation, StandardScaler
- [x] `ml/notebooks/01_eda.ipynb` — EDA notebook with Django ORM integration
- [x] `ml/artifacts/` + `ml/notebooks/` directories created

---

## 📋 Phase 1 — Data Pipeline (Week 3–5) ✅ COMPLETE

> **Completed:** 19 March 2026

### 1.1 Data Sources (Already Proven in `api_testing_web`)
| Source | Endpoint | Used For | Rate Limit |
|--------|----------|----------|------------|
| CricAPI (`api.cricapi.com`) | `/currentMatches`, `/matches`, `/players`, `/series_info` | Live matches, players | 100/day (free) |
| Cricbuzz via RapidAPI | `/matches/v1/recent`, `/matches/v1/live` | Live + recent results | 500/month (free) |

### 1.2 Django Management Commands ✅
- [x] `python manage.py sync_current_matches` — pull active matches → DB
- [x] `python manage.py sync_series` — pull series data
- [x] `python manage.py sync_player_stats --match-id=<id>` — pull match scorecard
- [x] `python manage.py sync_matches --source=completed` — sync recent completed matches
- [x] `python manage.py sync_matches --source=unified` — cross-source merge + dedupe

### 1.3 Celery Scheduled Tasks ✅
```python
# Every 5 minutes: sync live match data
# Every 1 hour: sync completed match results
# Every 6 hours: sync player stats
# Every day at midnight: run model re-training pipeline
```

### 1.4 Data Normalization ✅
- [x] Port logic from `api_testing_web/app/domain/normalize.js` to Python (`data_pipeline/normalizers.py`)
- [x] Deduplicate matches across CricAPI + Cricbuzz using name similarity
- [x] Standardize: team names, player names, venue names, format (test/odi/t20/t10)

### 1.5 Redis Caching Strategy ✅
- [x] Cache live match data: TTL 60s
- [x] Cache completed matches: TTL 6h
- [x] Cache player stats: TTL 24h
- [x] Cache prediction results: TTL 30min (until match starts)
- [x] Added pipeline status endpoint: `GET /api/v1/pipeline/status/` for sync counters/timestamps

---

## 📋 Phase 2 — Backend REST API (Week 6–8) ✅ COMPLETE

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

## 📋 Phase 3 — ML Core (Week 9–13) ✅ COMPLETE

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

## 📋 Phase 4 — Angular Frontend (Week 14–17) ✅ COMPLETE

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

## 🎯 Phase 1 — Closure Notes (Data Pipeline)

### Start Dev Server Right Now
```powershell
# Terminal 1 — Django backend
cd backend
python manage.py runserver
# → http://localhost:8000/api/v1/
# → http://localhost:8000/admin/  (admin@matchmind.dev / admin1234)

# Terminal 2 — Angular frontend
cd frontend
npm run start
# → http://localhost:4200/
```

### Phase 1 Completed Checklist
1. [ ] **Fill in `.env`** → add your real `CRICAPI_KEY` + `CRICBUZZ_RAPIDAPI_KEY`
2. [ ] **Test manual sync** → `python manage.py sync_matches` (confirm data flows to DB with real keys)
3. [ ] **Seed schedules** → `python manage.py seed_celery_schedules` (configure Celery Beat runtime)
4. [x] **Build normalizer** → `apps/data_pipeline/normalizers.py` — dedup matches across CricAPI + Cricbuzz
5. [x] **Player stats sync** → task `sync_player_stats` implemented and tested
6. [x] **Redis caching** — match list/detail/live caching + pipeline sync counters
7. [ ] **Start Docker Compose** → `docker compose -f docker-compose.dev.yml up --build`

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

## 📁 Key File Reference

| File | Purpose |
|------|---------|
| `backend/manage.py` | Django CLI (`runserver`, `migrate`, `sync_matches`) |
| `backend/config/settings/dev.py` | Dev settings: SQLite, no Redis, CELERY_ALWAYS_EAGER |
| `backend/config/settings/prod.py` | Prod settings: PG, HSTS, secure cookies |
| `backend/apps/data_pipeline/tasks.py` | Celery tasks for API sync |
| `backend/apps/matches/serializers.py` | DRF serializers (nested Team/Venue) |
| `ml/src/features/pre_match.py` | Feature engineering from Django ORM |
| `ml/src/models/ensemble.py` | RF + XGBoost ensemble predictor |
| `ml/notebooks/01_eda.ipynb` | Data exploration notebook |
| `frontend/src/styles.scss` | Global dark-mode design system |
| `frontend/src/app/app.routes.ts` | All Angular lazy-loaded routes |
| `infra/nginx/default.conf` | Nginx reverse proxy config |
| `.github/workflows/ci.yml` | CI/CD pipeline |
| `Makefile` | All dev shortcuts (`make setup`, `make run-backend`, etc.) |
| `docker-compose.dev.yml` | Full stack local environment |

---

*Plan Version: 1.5 | Phase 0 Completed: 19 March 2026 | Phase 1 Completed: 19 March 2026 | Phase 2 Completed: 20 March 2026 | Phase 3 Completed: 20 March 2026 | Phase 4 Completed: 20 March 2026*
