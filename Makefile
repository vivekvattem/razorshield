.PHONY: setup test lint migrate migration-check run docker-up docker-down data-generate data-validate features train evaluate

setup:
	python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e "./backend[dev]"

test:
	cd backend && ../.venv/bin/python -m pytest

lint:
	cd backend && ../.venv/bin/python -m ruff check app tests

migrate:
	cd backend && ../.venv/bin/python -m alembic upgrade head

migration-check:
	cd backend && ../.venv/bin/python -m alembic upgrade head && ../.venv/bin/python -m alembic check

run:
	cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

data-generate:
	cd backend && ../.venv/bin/python scripts/generate_synthetic_data.py

data-validate:
	cd backend && ../.venv/bin/python scripts/validate_synthetic_data.py

features:
	cd backend && ../.venv/bin/python -c "from app.risk.offline import build_features; print(build_features(__import__('pathlib').Path('../data/generated/default'))[0].shape)"

train:
	cd backend && ../.venv/bin/python scripts/run_offline_detector.py

evaluate: train
