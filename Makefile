<<<<<<< HEAD
.PHONY: setup test lint migrate migration-check run docker-up docker-down data-generate data-validate
=======
.PHONY: setup test lint migrate migration-check run docker-up docker-down
>>>>>>> 58e2af2715e314de060b741992c07c170726891e

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
<<<<<<< HEAD
	cd backend && ../.venv/bin/python -m alembic upgrade head && ../.venv/bin/python -m alembic check
=======
	cd backend && ../.venv/bin/python -m alembic check
>>>>>>> 58e2af2715e314de060b741992c07c170726891e

run:
	cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
<<<<<<< HEAD

data-generate:
	cd backend && ../.venv/bin/python scripts/generate_synthetic_data.py

data-validate:
	cd backend && ../.venv/bin/python scripts/validate_synthetic_data.py
=======
>>>>>>> 58e2af2715e314de060b741992c07c170726891e
