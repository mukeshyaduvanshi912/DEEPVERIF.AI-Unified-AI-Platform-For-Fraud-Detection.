#!/usr/bin/env bash
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Please install Python3"; exit 1; }
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Open in your browser: http://localhost:${PORT:-5000}   (press Ctrl+C to stop)"
python app.py
