# ═══════════════════════════════════════════════════════════
# MatchMind (Multi-Sport Prediction Platform) — Developer Makefile
# ═══════════════════════════════════════════════════════════
# Usage:  make <target>
# Requires: Python 3.11+, Node 20+, Docker Desktop

.PHONY: help install setup migrate superuser seed sync run-backend run-frontend \
        run-all test-backend build-frontend lint clean docker-up docker-down

# Default Python settings
DJANGO_SETTINGS ?= config.settings.dev
BACKEND_DIR     := backend
FRONTEND_DIR    := frontend
ML_DIR          := ml

help:   ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Installation ────────────────────────────────────────────
install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install Python backend dependencies
	cd $(BACKEND_DIR) && pip install -r requirements.txt

install-frontend: ## Install Angular frontend dependencies
	cd $(FRONTEND_DIR) && npm ci

# ── Database ─────────────────────────────────────────────────
migrate: ## Apply Django migrations
	cd $(BACKEND_DIR) && python manage.py migrate --settings=$(DJANGO_SETTINGS)

makemigrations: ## Create new Django migrations
	cd $(BACKEND_DIR) && python manage.py makemigrations --settings=$(DJANGO_SETTINGS)

# ── Dev Setup ────────────────────────────────────────────────
setup: install migrate superuser seed ## Full dev setup (install + migrate + superuser + seed)
	@echo "\n✅ Dev environment ready!"
	@echo "   Backend : http://localhost:8000/api/v1/"
	@echo "   Admin   : http://localhost:8000/admin/"
	@echo "   Frontend: http://localhost:4200/"

superuser: ## Create dev superuser (admin@cricket.dev / admin1234)
	cd $(BACKEND_DIR) && python manage.py create_dev_superuser --settings=$(DJANGO_SETTINGS)

seed: ## Seed Celery Beat schedules into DB
	cd $(BACKEND_DIR) && python manage.py seed_celery_schedules --settings=$(DJANGO_SETTINGS)

sync: ## Sync cricket data from APIs right now
	cd $(BACKEND_DIR) && python manage.py sync_matches --settings=$(DJANGO_SETTINGS)

# ── Running Servers ──────────────────────────────────────────
run-backend: ## Start Django dev server on :8000
	cd $(BACKEND_DIR) && python manage.py runserver 0.0.0.0:8000 --settings=$(DJANGO_SETTINGS)

run-frontend: ## Start Angular dev server on :4200
	cd $(FRONTEND_DIR) && npm run start

# ── Testing ──────────────────────────────────────────────────
test-backend: ## Run Django/pytest test suite
	cd $(BACKEND_DIR) && pytest --settings=$(DJANGO_SETTINGS) -v

test-frontend: ## Run Angular unit tests
	cd $(FRONTEND_DIR) && npm test -- --watch=false

# ── Build ─────────────────────────────────────────────────────
build-frontend: ## Build Angular for production
	cd $(FRONTEND_DIR) && npm run build -- --configuration=production

collectstatic: ## Collect Django static files
	cd $(BACKEND_DIR) && python manage.py collectstatic --no-input --settings=$(DJANGO_SETTINGS)

# ── Code Quality ─────────────────────────────────────────────
lint: ## Lint Python (flake8) + TypeScript (ng lint)
	cd $(BACKEND_DIR) && flake8 apps/ config/ --max-line-length=120
	cd $(FRONTEND_DIR) && npm run lint --if-present

# ── Docker ───────────────────────────────────────────────────
docker-up: ## Start full stack with Docker Compose (dev)
	docker compose -f docker-compose.dev.yml up --build

docker-down: ## Stop Docker Compose stack
	docker compose -f docker-compose.dev.yml down -v

docker-logs: ## Tail Docker Compose logs
	docker compose -f docker-compose.dev.yml logs -f

# ── ML ───────────────────────────────────────────────────────
train-model: ## Run ML model training script
	cd $(ML_DIR) && python src/models/train.py

notebook: ## Start Jupyter notebook server for ML exploration
	cd $(ML_DIR) && jupyter notebook notebooks/

# ── Clean ─────────────────────────────────────────────────────
clean: ## Remove Python caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf $(FRONTEND_DIR)/dist $(BACKEND_DIR)/staticfiles
	@echo "Cleaned!"
