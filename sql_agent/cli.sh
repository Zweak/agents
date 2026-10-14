#!/usr/bin/env bash
# Flexible CLI runner script
set -e

# Auto-activate venv if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
elif [ -f "venv/Scripts/activate" ]; then
    source "venv/Scripts/activate"
fi

python cli.py "$@"
