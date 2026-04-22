#!/bin/bash
# Build canisters and extract wasm/did artifacts
# Usage: ./token/scripts/build_canister.sh [output_dir]

set -e

OUTPUT_DIR="${1:-artifacts}"

# Navigate to token dir if we're at repo root
if [ -d "token/src" ]; then
    cd token
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
echo "Building token_backend canister..."
dfx canister create token_backend
dfx build token_backend

# Copy backend artifacts
cp .basilisk/token_backend/token_backend.wasm "$OUTPUT_DIR/"
cp src/token_backend/token_backend.did "$OUTPUT_DIR/"
gzip -k "$OUTPUT_DIR/token_backend.wasm"

# Build frontend canister
echo "Building token_frontend canister..."
echo "Installing frontend dependencies..."
cd src/token_frontend && npm install && cd ../..
dfx canister create token_frontend
dfx build token_frontend

# Copy frontend artifacts
cp .dfx/local/canisters/token_frontend/assetstorage.wasm.gz "$OUTPUT_DIR/token_frontend.wasm.gz"
gunzip -k "$OUTPUT_DIR/token_frontend.wasm.gz"
cp .dfx/local/canisters/token_frontend/assetstorage.did "$OUTPUT_DIR/token_frontend.did"

# Build info
echo "Build Date: $(date -u)" > "$OUTPUT_DIR/BUILD_INFO.txt"
echo "Git SHA: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')" >> "$OUTPUT_DIR/BUILD_INFO.txt"

echo "✅ Artifacts built successfully:"
ls -la "$OUTPUT_DIR/"
