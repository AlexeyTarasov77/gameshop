mkdir -p src/$1/domain
cd src/$1
touch __init__.py handlers.py models.py repositories.py schemas.py domain/services.py domain/interfaces.py domain/__init__.py
