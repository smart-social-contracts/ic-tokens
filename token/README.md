# Simple Token - ICRC-1

A simple ICRC-1 token implementation using Kybra (Python CDK for the Internet Computer).

## Features

- **ICRC-1 Standard Compliant**: Implements core ICRC-1 token standard methods
- **Kybra Backend**: Written in Python using Kybra CDK
- **Simple Frontend**: Displays token name and total supply
- **Persistent Storage**: Uses `kybra-simple-db` for balance storage

## Token Configuration

- **Name**: Simple Token
- **Symbol**: SMPL
- **Decimals**: 8
- **Initial Supply**: 1,000,000,000 SMPL
- **Transfer Fee**: 0.0001 SMPL

## ICRC-1 Methods

| Method | Type | Description |
|--------|------|-------------|
| `icrc1_name` | Query | Returns token name |
| `icrc1_symbol` | Query | Returns token symbol |
| `icrc1_decimals` | Query | Returns decimal places |
| `icrc1_fee` | Query | Returns transfer fee |
| `icrc1_total_supply` | Query | Returns total supply |
| `icrc1_balance_of` | Query | Returns account balance |
| `icrc1_transfer` | Update | Transfer tokens |
| `icrc1_metadata` | Query | Returns token metadata |

## Prerequisites

- [dfx](https://internetcomputer.org/docs/current/developer-docs/setup/install) (v0.29.0+)
- Python 3.10+
- Node.js 18+

## Running Locally

```bash
# Start the local replica
dfx start --background

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd src/token_frontend && npm install && cd ../..

# Deploy canisters
dfx deploy
```

The frontend will be available at the URL shown after deployment.

## Testing with dfx

```bash
# Get token name
dfx canister call token_backend icrc1_name

# Get total supply
dfx canister call token_backend icrc1_total_supply

# Get your balance
dfx canister call token_backend get_my_balance

# Get all token info
dfx canister call token_backend get_token_info
```

## Project Structure

```
token/
├── dfx.json                 # DFX configuration
├── requirements.txt         # Python dependencies
└── src/
    ├── token_backend/       # Kybra backend
    │   ├── src/main.py      # ICRC-1 implementation
    │   └── token_backend.did # Candid interface
    └── token_frontend/      # SvelteKit frontend
        └── src/
            └── routes/+page.svelte
```
