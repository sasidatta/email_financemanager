#!/bin/bash

APP_DIR="/data01/emailhandler"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"

cd "$APP_DIR" || { echo "❌ Failed to access $APP_DIR"; exit 1; }

echo "🛑 Stopping containers..."
docker compose -f $COMPOSE_FILE down

echo "🔨 Rebuilding Flask app image..."
docker compose -f $COMPOSE_FILE build flask_app || { echo "❌ Build failed"; exit 1; }

echo "🚀 Starting containers..."
docker compose -f $COMPOSE_FILE up -d || { echo "❌ Failed to start containers"; exit 1; }

echo "✅ App is running at http://localhost:5000"
