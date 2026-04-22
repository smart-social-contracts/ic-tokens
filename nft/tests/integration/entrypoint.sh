#!/bin/bash
# Integration tests entrypoint for ICRC-7/ICRC-37 NFT backend
# Sets up dfx, deploys canister, then runs Python tests
#
# Usage: ./tests/integration/entrypoint.sh

set -e
set -x

echo "=========================================="
echo "  ICRC-7/ICRC-37 NFT Integration Tests"
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

echo "Deploying nft_backend..."
INIT_ARG='(record { name = "Test NFT Collection"; symbol = "TNFT"; description = opt "Integration test NFT collection"; supply_cap = null; test = opt true })'
dfx deploy nft_backend --mode reinstall --argument "$INIT_ARG" --yes

echo ""
echo "=========================================="
echo "  Running Python Tests"
echo "=========================================="
echo ""

# Run Python tests
python tests/integration/test_nft.py
TEST_EXIT_CODE=$?

echo ""
echo "Stopping dfx..."
dfx stop

exit $TEST_EXIT_CODE
