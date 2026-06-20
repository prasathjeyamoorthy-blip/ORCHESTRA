#!/bin/bash

# Script to restart the PAN RAG server

echo "🔄 Stopping existing server..."
pkill -f "python.*api/main.py"

# Wait for process to stop
sleep 2

echo "✅ Server stopped"
echo "🚀 Starting server..."

# Start the server
python api/main.py

