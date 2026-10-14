#!/usr/bin/env bash
# Run interactive presentation demo across the 5 core scenarios
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

echo "=================================================="
echo "🎬 SQL Debugging & Optimization Agent Demo Runner"
echo "=================================================="

python cli.py --demo
