# ic-tokens

ICRC-1 Token and ICRC-7/37 NFT canisters for the Internet Computer, built with [Basilisk](https://github.com/smart-social-contracts/basilisk) (Python CDK).

## Structure

- `token/` — ICRC-1 fungible token canister (backend + frontend)
- `nft/` — ICRC-7/ICRC-37 NFT canister (backend + frontend)

## Prerequisites

- [dfx](https://internetcomputer.org/docs/current/developer-docs/setup/install/) >= 0.24
- Python 3.10
- Node.js >= 18

## Quick Start

```bash
# Install Python dependencies
pip install -r token/requirements.txt

# Build token backend
cd token
dfx start --background --clean
dfx canister create token_backend
dfx build token_backend

# Build NFT backend
cd ../nft
dfx canister create nft_backend
dfx build nft_backend
```

## Build Scripts

```bash
# Build token canister and extract artifacts
./token/scripts/build_canister.sh [output_dir]

# Build NFT canister and extract artifacts
./nft/scripts/build_canister.sh [output_dir]
```

## License

MIT
