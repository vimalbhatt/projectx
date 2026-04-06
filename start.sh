#!/bin/bash
PID_FILE=".streamlit.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "App is already running (PID $(cat "$PID_FILE"))"
    exit 1
fi

streamlit run app.py &
echo $! > "$PID_FILE"
echo "App started (PID $!)"
