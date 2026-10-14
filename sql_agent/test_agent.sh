#!/usr/bin/env bash
# Run automated verification tests
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

echo "Running test suite..."
python -m unittest tests/test_scenarios.py
echo "All tests passed successfully!"
