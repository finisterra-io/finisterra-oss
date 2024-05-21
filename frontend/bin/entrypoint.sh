#!/bin/sh

# Extract credentials from DATABASE_URL
DB_USER=$(echo $DATABASE_URL | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASSWORD=$(echo $DATABASE_URL | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo $DATABASE_URL | sed -n 's|.*@\(.*\):.*|\1|p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo $DATABASE_URL | sed -n 's|.*/\([^?]*\)?.*|\1|p')
DB_SCHEMA=$(echo $DATABASE_URL | sed -n 's|.*schema=\([^&]*\).*|\1|p')

# Ensure that DB_PORT is correctly set
if [ -z "$DB_PORT" ]; then
  DB_PORT=5432
fi

# Wait for PostgreSQL to be ready
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Conditionally run Prisma migrations
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running Prisma migrations..."
  npx prisma migrate deploy
else
  echo "Skipping Prisma migrations..."
fi

# Start the application
npm start
