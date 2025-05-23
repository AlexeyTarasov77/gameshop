.PHONY: api/run api/run/test api/run/prod run/tests run/tests/docker migrations/new migrations/run api/deploy/prod api/deploy/test 

MODE ?= local

api/run:
	MODE=$(MODE) poetry run python src/main.py 

run/tests:
	MODE="local-tests" poetry run pytest

run/redis:
	docker run -v gameshop_redis-data:/data -p 6379:6379 -d --rm --name redis-stack redis/redis-stack:latest


run/tests/docker:
	MODE="prod-tests" docker exec gameshop_web "sh poetry run pytest"

migrations/new:
	MODE=local poetry run alembic revision --autogenerate -m "$(msg)"


migrations/run:
	MODE=$(MODE) poetry run alembic upgrade head 

api/deploy/prod:
	bash scripts/deploy.sh prod

api/deploy/test:
	bash scripts/deploy.sh prod-tests
