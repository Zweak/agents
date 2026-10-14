#!/usr/bin/env bash
# Run automated verification tests
set -e

echo "Running test suite..."
python -m unittest tests/test_scenarios.py
echo "All tests passed successfully!"
