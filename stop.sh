#!/bin/bash
PID_FILE=".streamlit.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. App may not be running."
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f "$PID_FILE"
    echo "App stopped (PID $PID)"
else
    rm -f "$PID_FILE"
    echo "App was not running. Cleaned up stale PID file."
fi
