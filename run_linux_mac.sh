#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "YouTube Stream Downloader"
echo "Open http://127.0.0.1:5000"
echo

python app.py
