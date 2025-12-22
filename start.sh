#!/bin/bash

echo "Starting ITISCUP Tournament API..."

# Run migrations
echo "Running database migrations..."
if alembic upgrade head; then
    echo "Migrations completed successfully"
else
    echo "WARNING: Migration failed, but continuing to start server..."
    echo "This might be okay if tables already exist"
fi

# Start server
echo "Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

