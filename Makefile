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

.PHONY: migrations/run
migrations/run:
	MODE=$(mode) poetry run alembic upgrade head 

.PHONY: api/deploy
api/deploy:
	rsync -aPzc --exclude '.git' -e 'ssh -p 9999' --delete ~/Desktop/Dev/python/fastAPI/gameshop/ root@185.42.14.137:/root/projects/gameshop
