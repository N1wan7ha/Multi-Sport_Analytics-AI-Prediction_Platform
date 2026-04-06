# MatchMind - Multi-Sport Prediction Platform

An AI-powered multi-sport analytics platform delivering real-time match predictions and insights with 86%+ accuracy. Currently focused on Cricket, with a scalable architecture designed to support Football, Basketball, and more.

## Key Features
- **Real-Time Predictions**: Live match probability models with websocket streaming.
- **Robust Data Pipelines**: Resilient multi-layered ingestion from Cricsheet, APILayer, CricAPI, and high-fidelity generic web scrapers.
- **Advanced ML Engine**: Multi-mode training (yearly, rolling, walk-forward) with automated best-model selection routines.
- **Vector Context Search**: Weaviate integration for deriving semantic pre-match analytical insights.
- **Dynamic Dashboard**: Responsive, premium Angular 17 UI with telemetry, dynamic news integration, and real-time scorecards.

## Technology Stack
- **Frontend**: Angular 17 (TypeScript, SCSS)
- **Backend**: Django 5 + Django REST Framework
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7 + Celery 5
- **AI/ML**: scikit-learn, XGBoost, TensorFlow, Weaviate
- **DevOps**: Docker Compose, Nginx, Prometheus, Grafana

## Project Structure

```text
matchmind/
├── backend/         ← Django REST API & Model Pipelines
├── frontend/        ← Angular 17 SPA & Dashboards
├── ml/              ← ML training notebooks + experimentation code
├── infra/           ← Nginx, Prometheus, Grafana configs
├── resources/       ← Docs, diagrams, datasets, prototypes
├── plan.md          ← Full development plan & roadmap
└── docker-compose.dev.yml
```

## Getting Started

### 1 Configuration
Copy the environment template and configure your external provider API keys:

```bash
cp .env.example .env
```

**Required API Keys:**
- `CRICAPI_KEY` — from [cricketdata.org](https://cricketdata.org)
- `CRICBUZZ_RAPIDAPI_KEY` — from [RapidAPI](https://rapidapi.com)
- `APILAYER_API_KEY` — from [apilayer.com](https://apilayer.com) (Optional, for bronze layer syncing)

### 2 Running Locally (Docker — Recommended)
Bootstrap the full stack seamlessly using Docker Compose:

```bash
docker compose -f docker-compose.dev.yml up --build
```
- **Backend API**: `http://localhost:8000/api/v1/`
- **Frontend UI**: `http://localhost:4200/`
- **Services**: DB (`:5432`), Redis (`:6379`), Weaviate (`:8080`)

### 3 Running Locally (Manual Setup)
**Backend Environment**
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate          # Uses SQLite by default in local dev
python manage.py create_dev_superuser  # admin@matchmind.dev / admin1234
python manage.py runserver
```

**Frontend Environment**
```bash
cd frontend
npm install
npm run start
```

## Machine Learning Engine
MatchMind provides comprehensive CLI tooling for robust model training and lifecycle management, adaptable to varying hardware constraints.

### Training Modes
Execute scalable, targeted training directly from the terminal:

```bash
cd backend

# Full-history training (Hardware intensive)
python manage.py train_models --mode full

# Rolling-window training (recent N years)
python manage.py train_models --mode rolling --years 3

# Explicit year-range training
python manage.py train_models --mode year-range --start-year 2018 --end-year 2024

# Walk-forward training (Time-series validation)
python manage.py train_models --mode walk-forward
```

### Low-Hardware Training (Year-by-Year)
For executing pipelines on environments with strict CPU/RAM limits:
```bash
# 1) Import datasets (CSV/JSON from resources/dataset)
python manage.py seed_cricsheet_dataset

# 2) Train models progressively per year
python manage.py seed_cricsheet_dataset --train --train-yearly --start-year 2010 --end-year 2024 --version-prefix v2.2
```

### Advanced ML Context & Inference
- **Auto-Model Selection:** Prediction inferences automatically select and utilize the best existing model artifact based on internal metrics (Accuracy, AUC-ROC, Brier Score) when `ML_AUTO_SELECT_BEST_MODEL=True`.
- **Vector Context Enhancement:** Pre-match probabilities are enriched via bounded shifts derived from historical semantics.
  ```bash
  # Enable via .env: ML_VECTOR_CONTEXT_ENABLED=True
  
  # Index historical matches into the Vector DB
  cd backend
  python manage.py sync_weaviate_context --limit 5000
  ```

### Inspecting Model Rankings
You can inspect ML artifact metrics directly via the Admin API:
```bash
GET /api/v1/admin/models/ranking/
Authorization: Bearer <admin_jwt_token>
```

## Data Integration & Pipelines
MatchMind supports agnostic multi-layered ingestion.

**APILayer Catalog Synchronization:**
Allows populating the Bronze persistence layer with rich sports payloads for downstream analysis.
```bash
cd backend
python manage.py sync_matches --source=apilayer
```

## Testing & Validation
Verify endpoint integrity, model logic, and UI compilation:

**Backend Suite:**
```bash
cd backend
python manage.py check
python manage.py test --verbosity 1
```

**Frontend Suite:**
```bash
cd frontend
npm run build
npm run test -- --watch=false --browsers=ChromeHeadless --progress=false
```
*Note: In select Windows environments, Karma may report specs as passed but exit non-zero due to browser disconnect latency.*

## Production Deployment
Configure and launch the Phase 6 production stack incorporating load balancing and monitoring:

```bash
# Start production services securely
docker compose -f docker-compose.prod.yml up --build -d

# Seed automated ingestion/prediction Celery schedules
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_celery_schedules
```

**Production Subsystems:**
- **App Gateway:** Nginx (`http://localhost/`) handling `/api/` and WebSocket `/ws/` termination.
- **Monitoring:** Prometheus (`:9090`)
- **Visualizations:** Grafana (`:3000` — `admin/admin1234`)
- **SSL Termination:** Integrated Certbot configurations available in `docker-compose.prod.yml`.

## Roadmap & Progress

| Phase | Segment | Status |
|-------|---------|--------|
| **0** | Foundation | ✅ Complete |
| **1** | Data Pipeline | ✅ Complete |
| **2** | Backend API | ✅ Complete |
| **3** | ML Core | ✅ Complete |
| **4** | Frontend | ✅ Complete |
| **5** | Live Prediction | ✅ Complete |
| **6** | DevOps & Monitoring | ✅ Complete |
| **7** | Polish & Launch | 🔄 In Progress |

---
*BUILD BY N1WAN7HA*
