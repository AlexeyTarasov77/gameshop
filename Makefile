.PHONY: api/run api/run/test api/run/prod run/tests run/tests/docker migrations/new migrations/run api/deploy/prod api/deploy/test

api/run:
	MODE="local" poetry run python src/main.py 

api/run/test:
	MODE="tests" poetry run python src/main.py 

api/run/prod:
	MODE="prod" poetry run python src/main.py 

run/tests:
	MODE="tests" poetry run pytest

run/tests/docker:
	MODE="tests" docker exec gameshop_web "sh poetry run pytest"

migrations/new:
	MODE=local poetry run alembic revision --autogenerate -m "$(msg)"

MODE ?= local

migrations/run:
	MODE=$(MODE) poetry run alembic upgrade head 

api/deploy/prod:
	bash deploy.sh prod

api/deploy/test:
	bash deploy.sh test

