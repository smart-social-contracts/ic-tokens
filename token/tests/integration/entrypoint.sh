#!/bin/bash
# Integration tests entrypoint for ICRC-1 token backend
# Sets up dfx, deploys canister, then runs Python tests
#
# Usage: ./tests/integration/entrypoint.sh

set -e
set -x

echo "=========================================="
echo "  ICRC-1 Token Integration Tests"
echo "=========================================="

echo "Installing dependencies..."
pip install -q -r requirements.txt

### Not needed when running fresh from CI
# echo "Cleaning up any existing dfx..."
# bash scripts/clean_dfx.sh || true
# sleep 2

echo "Starting dfx..."
dfx start --clean --background
sleep 3

echo "Setting up test identities..."
dfx identity new test_alice --storage-mode plaintext 2>/dev/null || true
dfx identity new test_bob --storage-mode plaintext 2>/dev/null || true
dfx identity new test_charlie --storage-mode plaintext 2>/dev/null || true

echo "Deploying token_backend..."
INIT_ARG='(record { name = "Simple Token"; symbol = "SMPL"; decimals = 8 : nat8; total_supply = 100000000000000000 : nat; fee = 10000 : nat; test = opt true })'
dfx deploy token_backend --mode reinstall --argument "$INIT_ARG" --yes

echo ""
echo "=========================================="
echo "  Running Python Tests"
echo "=========================================="
echo ""

# Run Python tests
python tests/integration/test_token.py
TEST_EXIT_CODE=$?

echo ""
echo "Stopping dfx..."
dfx stop

exit $TEST_EXIT_CODE
