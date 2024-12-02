.PHONY: api/run
api/run:
	poetry run python src/main.py --config-path=config/prod.yaml
