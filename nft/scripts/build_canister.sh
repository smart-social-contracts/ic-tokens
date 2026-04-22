#!/bin/bash
# Build NFT canisters and extract wasm/did artifacts
# Usage: ./nft/scripts/build_canister.sh [output_dir]

set -e

OUTPUT_DIR="${1:-artifacts}"

# Navigate to nft dir if we're at repo root
if [ -d "nft/src" ]; then
    cd nft
    # Adjust output dir for relative paths
    if [[ "$OUTPUT_DIR" != /* ]]; then
        OUTPUT_DIR="../$OUTPUT_DIR"
    fi
fi

mkdir -p "$OUTPUT_DIR"

# Start dfx if not running
if ! dfx ping &>/dev/null; then
    echo "Starting dfx..."
    dfx start --background --clean
    sleep 2
fi

# Build backend canister
echo "Building nft_backend canister..."
dfx canister create nft_backend
dfx build nft_backend

# Copy backend artifacts
cp .basilisk/nft_backend/nft_backend.wasm "$OUTPUT_DIR/"
cp src/nft_backend/nft_backend.did "$OUTPUT_DIR/"
gzip -k "$OUTPUT_DIR/nft_backend.wasm"

# Build frontend canister
echo "Building nft_frontend canister..."
echo "Installing frontend dependencies..."
cd src/nft_frontend && npm install && cd ../..
dfx canister create nft_frontend
dfx build nft_frontend

# Copy frontend artifacts
cp .dfx/local/canisters/nft_frontend/assetstorage.wasm.gz "$OUTPUT_DIR/nft_frontend.wasm.gz"
gunzip -k "$OUTPUT_DIR/nft_frontend.wasm.gz"
cp .dfx/local/canisters/nft_frontend/assetstorage.did "$OUTPUT_DIR/nft_frontend.did"

# Build info
echo "NFT Build Date: $(date -u)" >> "$OUTPUT_DIR/BUILD_INFO.txt"

echo "✅ NFT artifacts built successfully:"
ls -la "$OUTPUT_DIR/nft_"*
