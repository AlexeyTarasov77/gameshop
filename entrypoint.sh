#!/bin/sh

if [ "$MODE" = "prod" ]; then
    echo "Running in production mode"
    make api/run/prod
elif [ "$MODE" = "local" ]; then
    echo "Running in dev mode"
    make api/run
else
    echo "Unknown MODE: $MODE"
fi