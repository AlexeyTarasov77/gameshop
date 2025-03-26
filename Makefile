.PHONY: api/run api/run/test api/run/prod run/tests run/tests/docker migrations/new migrations/run api/deploy/prod api/deploy/test 

MODE ?= local

api/run:
	MODE=$(MODE) poetry run python src/main.py 

run/tests:
	MODE="local-test" poetry run pytest

run/tests/docker:
	MODE="prod-test" docker exec gameshop_web "sh poetry run pytest"

migrations/new:
	MODE=local poetry run alembic revision --autogenerate -m "$(msg)"


migrations/run:
	MODE=$(MODE) poetry run alembic upgrade head 

api/deploy/prod:
	bash scripts/deploy.sh prod

api/deploy/test:
	bash scripts/deploy.sh prod-test
