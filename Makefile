.PHONY: api/run
api/run:
	MODE="local" poetry run python src/main.py 

.PHONY: api/run/prod
api/run/prod:
	poetry run python src/main.py --config-path=config/prod.yaml

.PHONY: api/deploy
api/deploy:
	rsync -aPz --checksum --delete ~/Desktop/Dev/python/fastAPI/gameshop/ root@185.42.14.137:/root/projects/gameshop
