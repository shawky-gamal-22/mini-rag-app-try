#!/bin/bash
set -e 

# This script is used to start the MinIRAG service in a Docker container.
echo "Running Database migrations..."
cd /app/models/db_schemes/minirag/
alembic upgrade head
cd /app
exec "$@"