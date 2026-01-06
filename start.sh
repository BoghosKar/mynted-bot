#!/bin/bash
# Start script for running both Discord bot and webhook server

echo "Starting Mynted AI services..."

# Start webhook server in background
echo "Starting webhook server on port 8000..."
python webhook_server.py &
WEBHOOK_PID=$!

# Wait a moment for webhook server to start
sleep 2

# Start Discord bot
echo "Starting Discord bot..."
python main.py &
BOT_PID=$!

# Function to handle cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $WEBHOOK_PID 2>/dev/null
    kill $BOT_PID 2>/dev/null
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait $WEBHOOK_PID $BOT_PID
