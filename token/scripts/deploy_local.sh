#!/bin/bash
# Deploy canister locally and run basic tests
# Usage: ./token/scripts/deploy_local.sh [--clean]

set -e

CLEAN=false
if [ "$1" == "--clean" ]; then
    CLEAN=true
fi

# Navigate to token dir if we're at repo root
if [ -d "token/src" ]; then
    cd token
fi

# Start dfx
if [ "$CLEAN" = true ]; then
    echo "Starting dfx with clean state..."
    dfx stop 2>/dev/null || true
    dfx start --background --clean
elif lsof -ti:8000 >/dev/null 2>&1; then
    echo "dfx already running on port 8000"
else
    echo "Starting dfx..."
    dfx start --background
fi

sleep 2

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd src/token_frontend && npm install && cd ../..

# Deploy canisters (init_arg is in dfx.json)
echo "Deploying token_backend..."
dfx deploy token_backend --mode reinstall --argument '(record { name = "Simple Token"; symbol = "SMPL"; decimals = 8 : nat8; total_supply = 100_000_000_000_000_000 : nat; fee = 10_000 : nat; test = opt true })' --yes

echo "Deploying token_frontend..."
dfx deploy token_frontend --mode reinstall --yes

# Run basic tests
echo ""
echo "Running basic canister calls..."
echo "================================"

echo "Token Info:"
dfx canister call token_backend get_token_info

echo ""
echo "Token Name:"
dfx canister call token_backend icrc1_name

echo ""
echo "Token Symbol:"
dfx canister call token_backend icrc1_symbol

echo ""
echo "Total Supply:"
dfx canister call token_backend icrc1_total_supply

echo ""
echo "Owner:"
dfx canister call token_backend get_owner

echo ""
echo "✅ Local deployment successful!"
echo "Frontend URL: http://$(dfx canister id token_frontend).localhost:$(dfx info webserver-port)/"
