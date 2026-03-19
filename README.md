"""
Cricket Analytics Platform — Root README
"""

# 🏏 Cricket Analytics & Prediction Platform

An AI-powered multi-sport analytics platform that delivers real-time match predictions with 86%+ accuracy.

## 🏗️ Stack
- **Frontend**: Angular 17 (TypeScript, SCSS)
- **Backend**: Django 5 + Django REST Framework
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7 + Celery 5
- **AI/ML**: scikit-learn, XGBoost, TensorFlow
- **DevOps**: Docker Compose, Prometheus, Grafana

## 📁 Folder Structure

```
prediction_analytics-Platform/
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

## 📊 Development Progress

See [plan.md](plan.md) for the full 7-phase roadmap.

| Phase | Status |
|-------|--------|
| 0 — Foundation | ✅ Complete |
| 1 — Data Pipeline | 🔄 Next |
| 2 — Backend API | ⏳ Planned |
| 3 — ML Core | ⏳ Planned |
| 4 — Frontend | ⏳ Planned |
| 5 — Live Prediction | ⏳ Planned |
| 6 & 7 — DevOps & Launch | ⏳ Planned |

## 🔑 API Keys

Set in `.env` (copy from `.env.example`). Keys are for:
- `CRICAPI_KEY` — from [cricketdata.org](https://cricketdata.org)
- `CRICBUZZ_RAPIDAPI_KEY` — from [RapidAPI](https://rapidapi.com)
