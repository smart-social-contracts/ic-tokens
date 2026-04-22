# ICRC-7/ICRC-37 NFT Canister

A Kybra (Python) implementation of the ICRC-7 (NFT) and ICRC-37 (Approve & Transfer From) standards for the Internet Computer.

## Standards Implemented

- **[ICRC-7](https://github.com/dfinity/ICRC/blob/main/ICRCs/ICRC-7/ICRC-7.md)** - NFT Standard
- **[ICRC-37](https://github.com/dfinity/ICRC/blob/main/ICRCs/ICRC-37/ICRC-37.md)** - Approve & Transfer From

## Features

### ICRC-7 (NFT Base)
- Collection metadata (name, symbol, description)
- Token ownership tracking
- Token metadata per NFT
- Paginated token queries
- NFT transfers

### ICRC-37 (Approvals)
- Token-level approvals
- Collection-level approvals
- Approval expiration
- Transfer on behalf of owner (`transfer_from`)
- Revoke approvals

### Additional
- Mint functionality (test mode)
- Transaction history logging
- Supply cap enforcement

## Quick Start

### Prerequisites

- [DFX](https://internetcomputer.org/docs/current/developer-docs/setup/install) >= 0.15.0
- Python 3.10+
- [Kybra](https://demergent-labs.github.io/kybra/) 0.7.x

### Local Development

```bash
cd nft

# Install dependencies
pip install -r requirements.txt

# Start local replica
dfx start --clean --background

# Deploy
dfx deploy
```

### Configuration

The canister is initialized with:

```candid
(record {
    name = "Simple NFT";
    symbol = "SNFT";
    description = opt "A simple ICRC-7/ICRC-37 NFT collection";
    supply_cap = null;  // No cap, or set to a nat value
    test = opt true     // Enable test mode for minting
})
```

## API Reference

### ICRC-7 Query Methods

| Method | Description |
|--------|-------------|
| `icrc7_name()` | Collection name |
| `icrc7_symbol()` | Collection symbol |
| `icrc7_description()` | Collection description |
| `icrc7_total_supply()` | Total NFTs minted |
| `icrc7_supply_cap()` | Max supply (if set) |
| `icrc7_collection_metadata()` | All collection metadata |
| `icrc7_token_metadata(token_id)` | Metadata for specific token |
| `icrc7_owner_of(token_id)` | Owner of specific token |
| `icrc7_balance_of(account)` | NFT count for account |
| `icrc7_tokens(prev, take)` | Paginated list of all token IDs |
| `icrc7_tokens_of(account, prev, take)` | Paginated list of owned token IDs |

### ICRC-7 Update Methods

| Method | Description |
|--------|-------------|
| `icrc7_transfer(args)` | Transfer NFTs to another account |

### ICRC-37 Query Methods

| Method | Description |
|--------|-------------|
| `icrc37_is_approved(spender, from_subaccount, token_id)` | Check if spender is approved |
| `icrc37_get_token_approvals(token_id, prev, take)` | List token approvals |
| `icrc37_get_collection_approvals(owner, prev, take)` | List collection approvals |

### ICRC-37 Update Methods

| Method | Description |
|--------|-------------|
| `icrc37_approve_tokens(args)` | Approve spender for specific tokens |
| `icrc37_approve_collection(args)` | Approve spender for all owned tokens |
| `icrc37_revoke_token_approvals(args)` | Revoke token approvals |
| `icrc37_revoke_collection_approvals(args)` | Revoke collection approvals |
| `icrc37_transfer_from(args)` | Transfer on behalf of owner |

### Admin Methods

| Method | Description |
|--------|-------------|
| `mint(arg)` | Mint new NFT (test mode only) |
| `get_transactions(start, length)` | Get transaction history |

## Usage Examples

### Mint an NFT (Test Mode)

```bash
dfx canister call nft_backend mint '(record {
    token_id = 1;
    owner = record { owner = principal "aaaaa-aa"; subaccount = null };
    metadata = opt vec {
        record { "name"; variant { Text = "My NFT" } };
        record { "description"; variant { Text = "First NFT" } };
    }
})'
```

### Transfer an NFT

```bash
dfx canister call nft_backend icrc7_transfer '(vec {
    record {
        from_subaccount = null;
        to = record { owner = principal "xxxxx-xxxxx-xxxxx"; subaccount = null };
        token_id = 1;
        memo = null;
        created_at_time = null;
    }
})'
```

### Approve a Spender

```bash
dfx canister call nft_backend icrc37_approve_tokens '(vec {
    record {
        token_id = 1;
        approval_info = record {
            spender = record { owner = principal "yyyyy-yyyyy-yyyyy"; subaccount = null };
            from_subaccount = null;
            expires_at = null;
            memo = null;
            created_at_time = null;
        }
    }
})'
```

### Transfer From (Approved Spender)

```bash
dfx canister call nft_backend icrc37_transfer_from '(vec {
    record {
        spender_subaccount = null;
        from_ = record { owner = principal "aaaaa-aa"; subaccount = null };
        to = record { owner = principal "zzzzz-zzzzz-zzzzz"; subaccount = null };
        token_id = 1;
        memo = null;
        created_at_time = null;
    }
})'
```

## Architecture

```
nft/
├── dfx.json              # DFX configuration
├── requirements.txt      # Python dependencies
├── src/
│   └── nft_backend/
│       ├── src/
│       │   └── main.py   # ICRC-7/ICRC-37 implementation
│       └── nft_backend.did  # Candid interface
└── tests/                # Test files
```

### Database Entities

- **NFTToken** - Individual NFT with ID, owner, and metadata
- **NFTCollection** - Collection-level config (singleton)
- **NFTApproval** - Token and collection approval records
- **NFTTransactionLog** - Transaction history

## License

MIT
