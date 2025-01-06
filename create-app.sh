#!/bin/sh

set -e

read -p "Enter app name: " app_name
if [[ -z $app_name ]]; then
  echo "app_name is required"
fi
mkdir -p src/$app_name/domain
cd src/$app_name
touch __init__.py handlers.py models.py repositories.py schemas.py domain/services.py domain/interfaces.py domain/__init__.py
