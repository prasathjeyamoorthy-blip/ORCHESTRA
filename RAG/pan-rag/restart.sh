#!/bin/bash
# Quick restart script for the RAG server

echo "Stopping any existing RAG server..."
pkill -f "uvicorn main:app" 2>/dev/null || true

echo "Starting RAG server..."
cd "$(dirname "$0")"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &

echo "RAG server restarted! PID: $!"
echo "Logs will appear below..."
