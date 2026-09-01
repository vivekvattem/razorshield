.PHONY: setup test lint migrate migration-check run docker-up docker-down

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
