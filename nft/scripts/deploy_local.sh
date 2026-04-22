#!/bin/bash
# Deploy NFT canister locally and run basic tests
# Usage: ./nft/scripts/deploy_local.sh [--clean]

set -e

CLEAN=false
if [ "$1" == "--clean" ]; then
    CLEAN=true
fi

# Navigate to nft dir if we're at repo root
if [ -d "nft/src" ]; then
    cd nft
fi

# Start dfx
if [ "$CLEAN" = true ]; then
    echo "Starting dfx with clean state..."
    dfx stop 2>/dev/null || true
    rm -rf .dfx/local .kybra
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
cd src/nft_frontend && npm install && cd ../..

# Deploy canisters (init_arg is in dfx.json)
echo "Deploying nft_backend..."
dfx deploy nft_backend --mode reinstall --argument '(record { name = "Simple NFT"; symbol = "SNFT"; description = opt "A simple ICRC-7/ICRC-37 NFT collection"; supply_cap = null; test = opt true })' --yes

echo "Deploying nft_frontend..."
dfx deploy nft_frontend --mode reinstall --yes

# Run basic tests
echo ""
echo "Running basic canister calls..."
echo "================================"

echo "Collection Name:"
dfx canister call nft_backend icrc7_name

echo ""
echo "Collection Symbol:"
dfx canister call nft_backend icrc7_symbol

echo ""
echo "Total Supply:"
dfx canister call nft_backend icrc7_total_supply

echo ""
echo "Test Mode:"
dfx canister call nft_backend is_test_mode

echo ""
echo "✅ Local deployment successful!"
echo "Frontend URL: http://$(dfx canister id nft_frontend).localhost:$(dfx info webserver-port)/"
