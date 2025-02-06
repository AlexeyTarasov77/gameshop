.PHONY: api/run
api/run:
	MODE="local" poetry run python src/main.py 

.PHONY: api/run/test
api/run/test:
	MODE="tests" poetry run python src/main.py 

.PHONY: api/run/prod
api/run/prod:
	MODE="prod" poetry run python src/main.py 

.PHONY: run/tests
run/tests:
	MODE="tests" poetry run pytest

.PHONY: run/tests/docker
run/tests/docker:
	MODE="tests" docker exec gameshop_web "sh poetry run pytest"

.PHONY: migrations/new
migrations/new:
	MODE=local poetry run alembic revision --autogenerate -m "$(msg)"

MODE ?= local

.PHONY: migrations/run
migrations/run:
	MODE=$(MODE) poetry run alembic upgrade head 

.PHONY: api/deploy
api/deploy:
	rsync -aPzc --exclude '.git' -e 'ssh -p 9999' --delete ~/Desktop/Dev/python/fastAPI/gameshop/ www@185.42.14.137:/home/www/projects/gameshop && \
	ssh www@185.42.14.137 -p 9999 'cd ~/projects/gameshop && docker compose restart  web'

