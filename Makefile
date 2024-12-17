.PHONY: api/run
api/run:
	MODE="local" poetry run python src/main.py 

.PHONE: api/run/prod
api/run/prod:
	poetry run python src/main.py --config-path=config/prod.yaml