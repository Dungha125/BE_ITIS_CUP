#!/bin/bash

echo "Starting ITISCUP Tournament API..."

# Run migrations với retry logic
echo "Running database migrations..."
MAX_RETRIES=3
RETRY_COUNT=0
MIGRATION_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if alembic upgrade head; then
        echo "✅ Migrations completed successfully"
        MIGRATION_SUCCESS=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Migration failed, retrying ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 2
        else
            echo "❌ Migration failed after $MAX_RETRIES attempts"
            echo "⚠️  Continuing to start server, but some features may not work"
            echo "⚠️  Please check migration logs and run manually if needed: alembic upgrade head"
        fi
    fi
done

# Start server
echo "Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

