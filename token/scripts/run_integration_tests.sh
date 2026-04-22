#!/bin/bash
# Run integration tests against a real dfx replica
# Usage: ./token/scripts/run_integration_tests.sh

set -e

# Navigate to token dir if we're at repo root
if [ -d "token/src" ]; then
    cd token
fi

# Run the integration tests
echo "Running integration tests..."
bash tests/integration/entrypoint.sh
