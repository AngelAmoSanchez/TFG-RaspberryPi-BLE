.PHONY: install run test migrate upgrade downgrade clean docker-up docker-down

install:
	pip install -r requirements.txt

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

test-cov:
	pytest --cov=src --cov-report=html tests/

migrate:
	alembic revision --autogenerate -m "$(msg)"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

docker-rebuild:
	docker compose down
	docker compose build --no-cache backend
	docker compose up -d

format:
	black src/ tests/ --line-length=100
	isort src/ tests/ --profile black

lint:
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports
