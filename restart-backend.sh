#!/bin/bash

# Restart Backend Server Script

echo "🔄 Restarting PAN Assistant Backend Server..."
echo ""

# Navigate to backend directory
cd auth-app/backend || { echo "❌ Error: auth-app/backend directory not found"; exit 1; }

# Find and kill existing node processes running server.js
echo "🔍 Looking for existing server processes..."
PIDS=$(ps aux | grep "[n]ode.*server.js" | awk '{print $2}')

if [ -n "$PIDS" ]; then
  echo "🛑 Stopping existing server processes: $PIDS"
  echo "$PIDS" | xargs kill -9
  sleep 2
  echo "✅ Existing processes stopped"
else
  echo "ℹ️  No existing server processes found"
fi

# Start the server
echo ""
echo "🚀 Starting backend server..."
echo ""

node server.js

# If you prefer to run in background, uncomment this instead:
# nohup node server.js > server.log 2>&1 &
# echo "✅ Server started in background (PID: $!)"
# echo "📋 Logs: auth-app/backend/server.log"
# echo ""
# echo "To view logs: tail -f auth-app/backend/server.log"
# echo "To stop: kill $!"
