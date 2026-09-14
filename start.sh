#!/bin/bash
set -e

echo "Starting FastAPI backend on port 8000..."
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Waiting for FastAPI backend to be ready..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
        echo "Backend is ready and healthy!"
        break
    fi
    sleep 1
done

echo "Starting Streamlit frontend on port ${PORT:-7860}..."
streamlit run frontend/streamlit_app.py --server.port "${PORT:-7860}" --server.address 0.0.0.0 &
FRONTEND_PID=$!

# Handle shutdown signals
trap "kill -TERM $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; exit" SIGINT SIGTERM

# Wait for either process to terminate
wait -n $BACKEND_PID $FRONTEND_PID
