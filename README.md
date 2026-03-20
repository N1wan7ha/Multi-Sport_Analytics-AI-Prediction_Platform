# 🎣 MatchMind — Multi-Sport Prediction Platform

An AI-powered multi-sport analytics platform that delivers real-time match predictions and insights across cricket, football, basketball, and more with 86%+ accuracy.

## 🏗️ Stack
- **Frontend**: Angular 17 (TypeScript, SCSS)
- **Backend**: Django 5 + Django REST Framework
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7 + Celery 5
- **AI/ML**: scikit-learn, XGBoost, TensorFlow
- **DevOps**: Docker Compose, Prometheus, Grafana

## 📁 Folder Structure

```
matchmind/
├── backend/         ← Django REST API
├── frontend/        ← Angular 17 SPA
├── ml/              ← ML training notebooks + model code
├── infra/           ← Nginx, Prometheus, Grafana configs
├── resources/       ← Docs, diagrams, prototypes (reference only)
├── plan.md          ← Full development plan
└── docker-compose.dev.yml
```

## 🚀 Quick Start (Local Dev — No Docker)

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate          # uses SQLite by default in dev
python manage.py create_dev_superuser  # admin@matchmind.dev / admin1234
python manage.py runserver
# → http://localhost:8000/api/v1/
# → http://localhost:8000/admin/
```

### Frontend
```bash
cd frontend
npm install
npm run start
# → http://localhost:4200/
```

## 🐳 Full Stack with Docker

```bash
# Copy and fill in your env vars
cp .env.example .env

# Start everything
docker compose -f docker-compose.dev.yml up --build

# Services:
# Backend  → http://localhost:8000
# Frontend → http://localhost:4200
# DB       → localhost:5432
# Redis    → localhost:6379
```

## 🚢 Production Stack (Phase 6)

```bash
# Start production-oriented stack
docker compose -f docker-compose.prod.yml up --build -d

# Seed Celery schedules (includes live prediction auto-trigger task)
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_celery_schedules
```

### Production Services
- App entrypoint via Nginx: http://localhost/
- Django API proxied at /api/
- WebSocket endpoint proxied at /ws/predictions/match/{match_id}/
- Prometheus: http://localhost:9090/
- Grafana: http://localhost:3000/ (admin/admin1234 unless overridden)

### Monitoring & Alerts
- Prometheus scrape config: infra/prometheus/prometheus.yml
- Alert rules: infra/prometheus/alerts.yml
- Grafana provisioning: infra/grafana/provisioning/
- Starter dashboard: infra/grafana/dashboards/platform-overview.json

### SSL Termination (Let's Encrypt)
- Nginx production config includes placeholders for ACME challenge path.
- Mount certbot volumes (already declared in docker-compose.prod.yml) and wire your certbot job on host.

## 📊 Development Progress

See [plan.md](plan.md) for the full 7-phase roadmap.

| Phase | Status |
|-------|--------|
| 0 — Foundation | ✅ Complete |
| 1 — Data Pipeline | ✅ Complete |
| 2 — Backend API | ✅ Complete |
| 3 — ML Core | ✅ Complete |
| 4 — Frontend | ✅ Complete |
| 5 — Live Prediction | ✅ Complete |
| 6 — DevOps & Monitoring | ✅ Complete |
| 7 — Polish & Launch | 🔄 In Progress |

## ✅ Validation Checklist

Run these commands to verify the current codebase end-to-end.

### Backend
```bash
cd backend
python manage.py check
python manage.py test --verbosity 1
```

### Frontend
```bash
cd frontend
npm run build
npm run test -- --watch=false --browsers=ChromeHeadless --progress=false
```

Note: in some Windows environments, Karma may report all specs as passed but still exit non-zero with a browser reload/disconnect message.

## 🔑 API Keys

Set in `.env` (copy from `.env.example`). Keys are for:
- `CRICAPI_KEY` — from [cricketdata.org](https://cricketdata.org)
- `CRICBUZZ_RAPIDAPI_KEY` — from [RapidAPI](https://rapidapi.com)
