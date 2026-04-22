#!/bin/bash
# Run backend tests locally
# Usage: ./token/scripts/run_tests.sh

set -e

echo "Running backend tests..."

# Navigate to token dir if we're at repo root
if [ -d "token/tests" ]; then
    cd token
fi

python3 tests/backend/test_token.py

echo "✅ All tests passed!"
