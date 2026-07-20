"""
ICRC-7 / ICRC-37 NFT Canister Implementation

This module implements the ICRC-7 (NFT) and ICRC-37 (Approve & Transfer From) standards
for the Internet Computer using Basilisk (Python CDK).

ICRC-7: https://github.com/dfinity/ICRC/blob/main/ICRCs/ICRC-7/ICRC-7.md
ICRC-37: https://github.com/dfinity/ICRC/blob/main/ICRCs/ICRC-37/ICRC-37.md
"""

from basilisk import (
    Alias,
    Async,
    CallResult,
    init,
    nat,
    nat8,
    nat32,
    nat64,
    blob,
    null,
    Opt,
    Principal,
    query,
    Record,
    StableBTreeMap,
    Tuple,
    update,
    Variant,
    Vec,
    void,
    ic,
    text,
)
from ic_python_db import Database, Entity, Integer, String
from ic_python_logging import get_logger

# Initialize stable storage for the database
storage = StableBTreeMap[str, str](
    memory_id=1, max_key_size=200, max_value_size=100_000
)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("nft_backend")

# =============================================================================
# Type Definitions (ICRC-7 / ICRC-37)
# =============================================================================

class Account(Record):
    owner: Principal
    subaccount: Opt[blob]


class TransferArg(Record):
    from_subaccount: Opt[blob]
    to: Account
    token_id: nat
    memo: Opt[blob]
    created_at_time: Opt[nat64]


class TransferError(Variant, total=False):
    NonExistingTokenId: null
    InvalidRecipient: null
    Unauthorized: null
    TooOld: null
    CreatedInFuture: "CreatedInFutureError"
    Duplicate: "DuplicateError"
    GenericError: "GenericError"
    GenericBatchError: "GenericBatchError"


class CreatedInFutureError(Record):
    ledger_time: nat64


class DuplicateError(Record):
    duplicate_of: nat


class GenericError(Record):
    error_code: nat
    message: str


class GenericBatchError(Record):
    error_code: nat
    message: str


class TransferResult(Variant, total=False):
    Ok: nat
    Err: TransferError


class ApprovalInfo(Record):
    spender: Account
    from_subaccount: Opt[blob]
    expires_at: Opt[nat64]
    memo: Opt[blob]
    created_at_time: Opt[nat64]


class ApproveTokenArg(Record):
    token_id: nat
    approval_info: ApprovalInfo


class ApproveTokenError(Variant, total=False):
    NonExistingTokenId: null
    Unauthorized: null
    TooOld: null
    CreatedInFuture: "CreatedInFutureError"
    GenericError: "GenericError"
    GenericBatchError: "GenericBatchError"


class ApproveTokenResult(Variant, total=False):
    Ok: nat
    Err: ApproveTokenError


class ApproveCollectionArg(Record):
    approval_info: ApprovalInfo


class ApproveCollectionError(Variant, total=False):
    TooOld: null
    CreatedInFuture: "CreatedInFutureError"
    GenericError: "GenericError"
    GenericBatchError: "GenericBatchError"


class ApproveCollectionResult(Variant, total=False):
    Ok: nat
    Err: ApproveCollectionError


class RevokeTokenApprovalArg(Record):
    token_id: nat
    spender: Opt[Account]
    from_subaccount: Opt[blob]
    memo: Opt[blob]
    created_at_time: Opt[nat64]


class RevokeTokenApprovalError(Variant, total=False):
    NonExistingTokenId: null
    Unauthorized: null
    ApprovalDoesNotExist: null
    TooOld: null
    CreatedInFuture: "CreatedInFutureError"
    GenericError: "GenericError"
    GenericBatchError: "GenericBatchError"


class RevokeTokenApprovalResult(Variant, total=False):
    Ok: nat
    Err: RevokeTokenApprovalError


class RevokeCollectionApprovalArg(Record):
    spender: Opt[Account]
    from_subaccount: Opt[blob]
    memo: Opt[blob]
    created_at_time: Opt[nat64]


class RevokeCollectionApprovalError(Variant, total=False):
    ApprovalDoesNotExist: null
    TooOld: null
    CreatedInFuture: "CreatedInFutureError"
    GenericError: "GenericError"
    GenericBatchError: "GenericBatchError"


class RevokeCollectionApprovalResult(Variant, total=False):
    Ok: nat
    Err: RevokeCollectionApprovalError


class TransferFromArg(Record):
    spender_subaccount: Opt[blob]
    from_: Account
    to: Account
    token_id: nat
    memo: Opt[blob]
    created_at_time: Opt[nat64]


class TransferFromError(Variant, total=False):
    NonExistingTokenId: null
    InvalidRecipient: null
    Unauthorized: null
    TooOld: null
    CreatedInFuture: "CreatedInFutureError"
    Duplicate: "DuplicateError"
    GenericError: "GenericError"
    GenericBatchError: "GenericBatchError"


class TransferFromResult(Variant, total=False):
    Ok: nat
    Err: TransferFromError


class TokenApproval(Record):
    token_id: nat
    approval_info: ApprovalInfo


class CollectionApproval(Record):
    approval_info: ApprovalInfo


# Metadata value types
class MetadataValue(Variant, total=False):
    Text: str
    Blob: blob
    Nat: nat
    Int: int


class InitArg(Record):
    name: str
    symbol: str
    description: Opt[str]
    supply_cap: Opt[nat]
    test: Opt[bool]


class MintArg(Record):
    token_id: Opt[nat]
    owner: Account
    metadata: Opt[Vec[Tuple[str, MetadataValue]]]


class MintError(Variant, total=False):
    Unauthorized: null
    TokenIdAlreadyExists: null
    SupplyCapReached: null
    GenericError: "GenericError"


class MintResult(Variant, total=False):
    Ok: nat
    Err: MintError


# Authority-controlled operations (ERC-3643/ERC-6147-style semantics).
# The registry authority (an authorized minter matching the token's authority
# metadata, or a canister controller) can force-transfer or freeze tokens.
class ForceTransferArg(Record):
    token_id: nat
    to: Account
    memo: Opt[str]


class FreezeArg(Record):
    token_id: nat
    reason: Opt[str]


class TransferAuthorityArg(Record):
    token_id: nat
    new_authority: Principal
    memo: Opt[str]


class AuthorityError(Variant, total=False):
    NonExistingTokenId: null
    Unauthorized: null
    InvalidRecipient: null
    GenericError: "GenericError"


class AuthorityResult(Variant, total=False):
    Ok: nat
    Err: AuthorityError


# Candid Record types for query returns
class StandardRecord(Record):
    name: str
    url: str


class TransactionRecord(Record):
    id: nat
    kind: str
    timestamp: nat64
    token_id: nat
    from_principal: str
    from_subaccount: str
    to_principal: str
    to_subaccount: str
    spender_principal: str
    spender_subaccount: str
    memo: str


# =============================================================================
# Database Entities
# =============================================================================

class NFTToken(Entity):
    """Individual NFT token with unique ID and owner."""
    __alias__ = "id"
    id = Integer()  # Token ID (nat)
    owner_principal = String()  # Owner's principal
    owner_subaccount = String(max_length=64, default="")  # Hex-encoded subaccount
    metadata_json = String(max_length=4096, default="{}")  # JSON-encoded metadata
    # Registry authority: the principal that minted the token (e.g. a realm
    # canister). Only this principal (or a canister controller) may
    # force-transfer or freeze the token.
    authority_principal = String(default="")
    frozen = Integer(default=0)  # 1 = transfers blocked
    frozen_reason = String(max_length=512, default="")


class NFTCollection(Entity):
    """Collection-level configuration (singleton)."""
    __alias__ = "id"
    id = String(max_length=16, default="config")
    name = String(max_length=256)
    symbol = String(max_length=32)
    description = String(max_length=1024, default="")
    supply_cap = Integer(default=0)  # 0 means no cap
    total_supply = Integer(default=0)
    next_token_id = Integer(default=1)  # Sequential ID for auto-assigned mints
    tx_count = Integer(default=0)  # Transaction counter for block indices
    test_mode = Integer(default=0)  # 1 = test mode enabled
    authorized_minters = String(max_length=8192, default="")  # comma-separated principals


class NFTApproval(Entity):
    """Token-level approval record."""
    __alias__ = "id"
    id = String()  # Format: "token:{token_id}:{owner}:{spender}" or "collection:{owner}:{spender}"
    approval_type = String(max_length=16)  # "token" or "collection"
    token_id = Integer(default=0)  # Only for token approvals
    owner_principal = String()
    owner_subaccount = String(max_length=64, default="")
    spender_principal = String()
    spender_subaccount = String(max_length=64, default="")
    expires_at = Integer(default=0)  # 0 means no expiry
    created_at = Integer(default=0)


class NFTTransactionLog(Entity):
    """Transaction history for ICRC-3 compatibility."""
    __alias__ = "id"
    id = Integer()  # Block index
    # "mint", "transfer", "approve", "approve_collection", "revoke",
    # "revoke_collection", "transfer_from", "force_transfer", "freeze", "unfreeze"
    kind = String(max_length=32)
    timestamp = Integer()  # Nanoseconds since epoch
    token_id = Integer()
    from_principal = String(default="")
    from_subaccount = String(max_length=64, default="")
    to_principal = String(default="")
    to_subaccount = String(max_length=64, default="")
    spender_principal = String(default="")  # For approve/transfer_from
    spender_subaccount = String(max_length=64, default="")
    memo = String(max_length=512, default="")


# Register entity types
Database.get_instance().register_entity_type(NFTToken)
Database.get_instance().register_entity_type(NFTCollection)
Database.get_instance().register_entity_type(NFTApproval)
Database.get_instance().register_entity_type(NFTTransactionLog)


# =============================================================================
# Helper Functions
# =============================================================================

def _account_to_str(account: Account) -> str:
    """Convert Account to string representation."""
    principal = account["owner"].to_str()
    subaccount = account.get("subaccount")
    if subaccount:
        return f"{principal}:{subaccount.hex()}"
    return principal


def _subaccount_to_hex(subaccount: Opt[blob]) -> str:
    """Convert optional subaccount to hex string."""
    if subaccount:
        return subaccount.hex()
    return ""


def _get_collection() -> NFTCollection:
    """Get or create collection config."""
    collection = NFTCollection["config"]
    if collection:
        return collection
    raise Exception("Collection not initialized")


def _ensure_next_token_id(collection: NFTCollection) -> None:
    """Initialize next_token_id for collections that predate the counter.

    Existing collections may have next_token_id defaulting to 1. If the
    collection already has tokens, bump the counter to one past the highest
    existing token ID so auto-assigned IDs never collide with existing ones.
    """
    if collection.next_token_id <= 1 and collection.total_supply > 0:
        max_id = max((int(t.id) for t in NFTToken.instances()), default=0)
        collection.next_token_id = max(max_id + 1, collection.next_token_id)


def _authorized_minter_set() -> set:
    collection = _get_collection()
    raw = getattr(collection, "authorized_minters", "") or ""
    return {p.strip() for p in raw.split(",") if p.strip()}


def _is_authorized_minter(principal_str: str) -> bool:
    return principal_str in _authorized_minter_set()


def _can_mint(caller) -> bool:
    collection = _get_collection()
    if collection.test_mode == 1:
        return True
    caller_str = caller.to_str()
    if _is_authorized_minter(caller_str):
        return True
    return False


def _is_token_authority(caller, token) -> bool:
    """Check whether the caller is the registry authority for the token.

    The authority is the principal recorded at mint time (e.g. the realm
    canister that minted it). Canister controllers can always act, which
    covers tokens minted before the authority field existed and provides
    an escape hatch for platform-level intervention.
    """
    if ic.is_controller(caller):
        return True
    caller_str = caller.to_str()
    authority = getattr(token, "authority_principal", "") or ""
    if authority and caller_str == authority and _is_authorized_minter(caller_str):
        return True
    return False


def _is_token_frozen(token) -> bool:
    return bool(getattr(token, "frozen", 0))


def _get_token(token_id: nat) -> Opt[NFTToken]:
    """Get token by ID."""
    return NFTToken[int(token_id)]


def _is_owner(token: NFTToken, account: Account) -> bool:
    """Check if account is the owner of the token."""
    if token.owner_principal != account["owner"].to_str():
        return False
    expected_sub = _subaccount_to_hex(account.get("subaccount"))
    return token.owner_subaccount == expected_sub


def _get_approval_id(approval_type: str, token_id: int, owner: Account, spender: Account) -> str:
    """Generate approval ID."""
    owner_str = _account_to_str(owner)
    spender_str = _account_to_str(spender)
    if approval_type == "token":
        return f"token:{token_id}:{owner_str}:{spender_str}"
    return f"collection:{owner_str}:{spender_str}"


def _is_approved(token: NFTToken, spender: Account) -> bool:
    """Check if spender is approved for the token (token-level or collection-level)."""
    now = ic.time()
    owner_account = Account(
        owner=Principal.from_str(token.owner_principal),
        subaccount=bytes.fromhex(token.owner_subaccount) if token.owner_subaccount else None
    )
    
    # Check token-level approval
    token_approval_id = _get_approval_id("token", token.id, owner_account, spender)
    approval = NFTApproval[token_approval_id]
    if approval:
        if approval.expires_at == 0 or approval.expires_at > now:
            return True
    
    # Check collection-level approval
    collection_approval_id = _get_approval_id("collection", 0, owner_account, spender)
    approval = NFTApproval[collection_approval_id]
    if approval:
        if approval.expires_at == 0 or approval.expires_at > now:
            return True
    
    return False


def _next_tx_id() -> int:
    """Get next transaction ID and increment counter."""
    collection = _get_collection()
    tx_id = collection.tx_count
    collection.tx_count = tx_id + 1
    return tx_id


def _log_transaction(
    kind: str,
    token_id: int,
    from_principal: str = "",
    from_subaccount: str = "",
    to_principal: str = "",
    to_subaccount: str = "",
    spender_principal: str = "",
    spender_subaccount: str = "",
    memo: str = ""
) -> int:
    """Log a transaction and return block index."""
    tx_id = _next_tx_id()
    tx = NFTTransactionLog(
        id=tx_id,
        kind=kind,
        timestamp=ic.time(),
        token_id=token_id,
        from_principal=from_principal,
        from_subaccount=from_subaccount,
        to_principal=to_principal,
        to_subaccount=to_subaccount,
        spender_principal=spender_principal,
        spender_subaccount=spender_subaccount,
        memo=memo
    )
    return tx_id


# =============================================================================
# Canister Lifecycle
# =============================================================================

@init
def init_(args: InitArg) -> void:
    """Initialize the NFT collection."""
    logger.info(f"Initializing NFT collection: {args['name']} ({args['symbol']})")
    
    NFTCollection(
        id="config",
        name=args["name"],
        symbol=args["symbol"],
        description=args.get("description") or "",
        supply_cap=args.get("supply_cap") or 0,
        total_supply=0,
        next_token_id=1,
        tx_count=0,
        test_mode=1 if args.get("test") else 0
    )
    logger.info("NFT collection initialized")


# =============================================================================
# ICRC-7 Query Methods
# =============================================================================

@query
def icrc7_name() -> str:
    """Returns the name of the NFT collection."""
    return _get_collection().name


@query
def icrc7_symbol() -> str:
    """Returns the symbol of the NFT collection."""
    return _get_collection().symbol


@query
def icrc7_description() -> Opt[str]:
    """Returns the description of the NFT collection."""
    desc = _get_collection().description
    return desc if desc else None


@query
def icrc7_total_supply() -> nat:
    """Returns the total number of NFTs in the collection."""
    return _get_collection().total_supply


@query
def icrc7_supply_cap() -> Opt[nat]:
    """Returns the maximum number of NFTs that can be minted, if any."""
    cap = _get_collection().supply_cap
    return cap if cap > 0 else None


@query
def icrc7_collection_metadata() -> Vec[Tuple[str, MetadataValue]]:
    """Returns collection-level metadata."""
    collection = _get_collection()
    metadata = [
        ("icrc7:name", MetadataValue(Text=collection.name)),
        ("icrc7:symbol", MetadataValue(Text=collection.symbol)),
        ("icrc7:total_supply", MetadataValue(Nat=collection.total_supply)),
    ]
    if collection.description:
        metadata.append(("icrc7:description", MetadataValue(Text=collection.description)))
    if collection.supply_cap > 0:
        metadata.append(("icrc7:supply_cap", MetadataValue(Nat=collection.supply_cap)))
    return metadata


@query
def icrc7_token_metadata(token_id: nat) -> Opt[Vec[Tuple[str, MetadataValue]]]:
    """Returns metadata for a specific token."""
    token = _get_token(token_id)
    if not token:
        return None
    
    import json
    try:
        meta_dict = json.loads(token.metadata_json)
    except:
        meta_dict = {}
    
    metadata = []
    for key, value in meta_dict.items():
        if isinstance(value, str):
            metadata.append((key, MetadataValue(Text=value)))
        elif isinstance(value, int):
            metadata.append((key, MetadataValue(Nat=value)))
    
    if _is_token_frozen(token):
        metadata.append(("frozen", MetadataValue(Nat=1)))
        if token.frozen_reason:
            metadata.append(("frozen_reason", MetadataValue(Text=token.frozen_reason)))
    
    return metadata


@query
def icrc7_owner_of(token_id: nat) -> Opt[Account]:
    """Returns the owner of the specified token."""
    token = _get_token(token_id)
    if not token:
        return None
    
    return Account(
        owner=Principal.from_str(token.owner_principal),
        subaccount=bytes.fromhex(token.owner_subaccount) if token.owner_subaccount else None
    )


@query
def icrc7_balance_of(account: Account) -> nat:
    """Returns the number of NFTs owned by the specified account."""
    principal = account["owner"].to_str()
    subaccount = _subaccount_to_hex(account.get("subaccount"))
    
    all_tokens = NFTToken.instances()
    count = 0
    for token in all_tokens:
        if token.owner_principal == principal and token.owner_subaccount == subaccount:
            count += 1
    return count


@query
def icrc7_tokens(prev: Opt[nat], take: Opt[nat]) -> Vec[nat]:
    """Returns a paginated list of all token IDs."""
    all_tokens = NFTToken.instances()
    token_ids = sorted([token.id for token in all_tokens])
    
    start_idx = 0
    if prev is not None:
        for i, tid in enumerate(token_ids):
            if tid > prev:
                start_idx = i
                break
        else:
            return []
    
    limit = take if take is not None else 100
    return token_ids[start_idx:start_idx + limit]


@query
def icrc7_tokens_of(account: Account, prev: Opt[nat], take: Opt[nat]) -> Vec[nat]:
    """Returns a paginated list of token IDs owned by the specified account."""
    principal = account["owner"].to_str()
    subaccount = _subaccount_to_hex(account.get("subaccount"))
    
    all_tokens = NFTToken.instances()
    owned_ids = sorted([
        token.id for token in all_tokens
        if token.owner_principal == principal and token.owner_subaccount == subaccount
    ])
    
    start_idx = 0
    if prev is not None:
        for i, tid in enumerate(owned_ids):
            if tid > prev:
                start_idx = i
                break
        else:
            return []
    
    limit = take if take is not None else 100
    return owned_ids[start_idx:start_idx + limit]


# =============================================================================
# ICRC-7 Update Methods
# =============================================================================

@update
def icrc7_transfer(args: Vec[TransferArg]) -> Vec[Opt[TransferResult]]:
    """Transfer NFTs from the caller to another account."""
    caller = ic.caller()
    results = []
    
    for arg in args:
        token = _get_token(arg["token_id"])
        
        if not token:
            results.append(TransferResult(Err=TransferError(NonExistingTokenId=null)))
            continue
        
        # Frozen tokens cannot be transferred by holders
        if _is_token_frozen(token):
            results.append(TransferResult(Err=TransferError(
                GenericError=GenericError(error_code=423, message="Token is frozen by the registry authority")
            )))
            continue
        
        # Build caller account
        caller_account = Account(
            owner=caller,
            subaccount=arg.get("from_subaccount")
        )
        
        # Check ownership
        if not _is_owner(token, caller_account):
            results.append(TransferResult(Err=TransferError(Unauthorized=null)))
            continue
        
        # Check recipient is not the same as sender
        to_account = arg["to"]
        if _is_owner(token, to_account):
            results.append(TransferResult(Err=TransferError(InvalidRecipient=null)))
            continue
        
        # Perform transfer
        old_owner = token.owner_principal
        old_subaccount = token.owner_subaccount
        
        token.owner_principal = to_account["owner"].to_str()
        token.owner_subaccount = _subaccount_to_hex(to_account.get("subaccount"))
        
        # Clear token-level approvals for this token
        all_approvals = NFTApproval.instances()
        for approval in all_approvals:
            if approval.approval_type == "token" and approval.token_id == int(arg["token_id"]):
                approval.delete()
        
        # Log transaction
        memo = arg.get("memo")
        tx_id = _log_transaction(
            kind="transfer",
            token_id=int(arg["token_id"]),
            from_principal=old_owner,
            from_subaccount=old_subaccount,
            to_principal=token.owner_principal,
            to_subaccount=token.owner_subaccount,
            memo=memo.hex() if memo else ""
        )
        
        logger.info(f"Transfer: token {arg['token_id']} from {old_owner} to {token.owner_principal}")
        results.append(TransferResult(Ok=tx_id))
    
    return results


# =============================================================================
# ICRC-37 Query Methods
# =============================================================================

@query
def icrc37_is_approved(spender: Account, from_subaccount: Opt[blob], token_id: nat) -> bool:
    """Check if spender is approved for the token."""
    token = _get_token(token_id)
    if not token:
        return False
    
    # Check if spender matches expected from_subaccount owner
    if from_subaccount:
        expected_sub = from_subaccount.hex()
        if token.owner_subaccount != expected_sub:
            return False
    
    return _is_approved(token, spender)


@query
def icrc37_get_token_approvals(token_id: nat, prev: Opt[Account], take: Opt[nat]) -> Vec[TokenApproval]:
    """Get all approvals for a specific token."""
    token = _get_token(token_id)
    if not token:
        return []
    
    all_approvals = NFTApproval.instances()
    token_approvals = [
        a for a in all_approvals
        if a.approval_type == "token" and a.token_id == int(token_id)
    ]
    
    # Filter expired
    now = ic.time()
    valid_approvals = [
        a for a in token_approvals
        if a.expires_at == 0 or a.expires_at > now
    ]
    
    # Pagination (simplified - not using prev for now)
    limit = take if take is not None else 100
    
    results = []
    for approval in valid_approvals[:limit]:
        results.append(TokenApproval(
            token_id=token_id,
            approval_info=ApprovalInfo(
                spender=Account(
                    owner=Principal.from_str(approval.spender_principal),
                    subaccount=bytes.fromhex(approval.spender_subaccount) if approval.spender_subaccount else None
                ),
                from_subaccount=bytes.fromhex(approval.owner_subaccount) if approval.owner_subaccount else None,
                expires_at=approval.expires_at if approval.expires_at > 0 else None,
                memo=None,
                created_at_time=approval.created_at if approval.created_at > 0 else None
            )
        ))
    
    return results


@query
def icrc37_get_collection_approvals(owner: Account, prev: Opt[Account], take: Opt[nat]) -> Vec[CollectionApproval]:
    """Get all collection-level approvals for an owner."""
    owner_principal = owner["owner"].to_str()
    owner_subaccount = _subaccount_to_hex(owner.get("subaccount"))
    
    all_approvals = NFTApproval.instances()
    collection_approvals = [
        a for a in all_approvals
        if a.approval_type == "collection"
        and a.owner_principal == owner_principal
        and a.owner_subaccount == owner_subaccount
    ]
    
    # Filter expired
    now = ic.time()
    valid_approvals = [
        a for a in collection_approvals
        if a.expires_at == 0 or a.expires_at > now
    ]
    
    limit = take if take is not None else 100
    
    results = []
    for approval in valid_approvals[:limit]:
        results.append(CollectionApproval(
            approval_info=ApprovalInfo(
                spender=Account(
                    owner=Principal.from_str(approval.spender_principal),
                    subaccount=bytes.fromhex(approval.spender_subaccount) if approval.spender_subaccount else None
                ),
                from_subaccount=bytes.fromhex(approval.owner_subaccount) if approval.owner_subaccount else None,
                expires_at=approval.expires_at if approval.expires_at > 0 else None,
                memo=None,
                created_at_time=approval.created_at if approval.created_at > 0 else None
            )
        ))
    
    return results


# =============================================================================
# ICRC-37 Update Methods
# =============================================================================

@update
def icrc37_approve_tokens(args: Vec[ApproveTokenArg]) -> Vec[Opt[ApproveTokenResult]]:
    """Approve a spender for specific tokens."""
    caller = ic.caller()
    results = []
    
    for arg in args:
        token = _get_token(arg["token_id"])
        
        if not token:
            results.append(ApproveTokenResult(Err=ApproveTokenError(NonExistingTokenId=null)))
            continue
        
        # Build caller account
        approval_info = arg["approval_info"]
        caller_account = Account(
            owner=caller,
            subaccount=approval_info.get("from_subaccount")
        )
        
        # Check ownership
        if not _is_owner(token, caller_account):
            results.append(ApproveTokenResult(Err=ApproveTokenError(Unauthorized=null)))
            continue
        
        # Create approval
        spender = approval_info["spender"]
        approval_id = _get_approval_id("token", int(arg["token_id"]), caller_account, spender)
        
        approval = NFTApproval(
            id=approval_id,
            approval_type="token",
            token_id=int(arg["token_id"]),
            owner_principal=caller.to_str(),
            owner_subaccount=_subaccount_to_hex(approval_info.get("from_subaccount")),
            spender_principal=spender["owner"].to_str(),
            spender_subaccount=_subaccount_to_hex(spender.get("subaccount")),
            expires_at=approval_info.get("expires_at") or 0,
            created_at=approval_info.get("created_at_time") or ic.time()
        )
        
        tx_id = _log_transaction(
            kind="approve",
            token_id=int(arg["token_id"]),
            from_principal=caller.to_str(),
            spender_principal=spender["owner"].to_str(),
            spender_subaccount=_subaccount_to_hex(spender.get("subaccount"))
        )
        
        logger.info(f"Approve: token {arg['token_id']} for spender {spender['owner'].to_str()}")
        results.append(ApproveTokenResult(Ok=tx_id))
    
    return results


@update
def icrc37_approve_collection(args: Vec[ApproveCollectionArg]) -> Vec[Opt[ApproveCollectionResult]]:
    """Approve a spender for all tokens owned by the caller."""
    caller = ic.caller()
    results = []
    
    for arg in args:
        approval_info = arg["approval_info"]
        caller_account = Account(
            owner=caller,
            subaccount=approval_info.get("from_subaccount")
        )
        spender = approval_info["spender"]
        
        approval_id = _get_approval_id("collection", 0, caller_account, spender)
        
        approval = NFTApproval(
            id=approval_id,
            approval_type="collection",
            token_id=0,
            owner_principal=caller.to_str(),
            owner_subaccount=_subaccount_to_hex(approval_info.get("from_subaccount")),
            spender_principal=spender["owner"].to_str(),
            spender_subaccount=_subaccount_to_hex(spender.get("subaccount")),
            expires_at=approval_info.get("expires_at") or 0,
            created_at=approval_info.get("created_at_time") or ic.time()
        )
        
        tx_id = _log_transaction(
            kind="approve_collection",
            token_id=0,
            from_principal=caller.to_str(),
            spender_principal=spender["owner"].to_str(),
            spender_subaccount=_subaccount_to_hex(spender.get("subaccount"))
        )
        
        logger.info(f"Approve collection for spender {spender['owner'].to_str()}")
        results.append(ApproveCollectionResult(Ok=tx_id))
    
    return results


@update
def icrc37_revoke_token_approvals(args: Vec[RevokeTokenApprovalArg]) -> Vec[Opt[RevokeTokenApprovalResult]]:
    """Revoke approvals for specific tokens."""
    caller = ic.caller()
    results = []
    
    for arg in args:
        token = _get_token(arg["token_id"])
        
        if not token:
            results.append(RevokeTokenApprovalResult(Err=RevokeTokenApprovalError(NonExistingTokenId=null)))
            continue
        
        caller_account = Account(
            owner=caller,
            subaccount=arg.get("from_subaccount")
        )
        
        # Check ownership
        if not _is_owner(token, caller_account):
            results.append(RevokeTokenApprovalResult(Err=RevokeTokenApprovalError(Unauthorized=null)))
            continue
        
        spender = arg.get("spender")
        if spender:
            # Revoke specific approval
            approval_id = _get_approval_id("token", int(arg["token_id"]), caller_account, spender)
            approval = NFTApproval[approval_id]
            if not approval:
                results.append(RevokeTokenApprovalResult(Err=RevokeTokenApprovalError(ApprovalDoesNotExist=null)))
                continue
            approval.delete()
        else:
            # Revoke all approvals for this token
            all_approvals = NFTApproval.instances()
            for approval in all_approvals:
                if approval.approval_type == "token" and approval.token_id == int(arg["token_id"]):
                    if approval.owner_principal == caller.to_str():
                        approval.delete()
        
        tx_id = _log_transaction(
            kind="revoke",
            token_id=int(arg["token_id"]),
            from_principal=caller.to_str()
        )
        
        logger.info(f"Revoke approval: token {arg['token_id']}")
        results.append(RevokeTokenApprovalResult(Ok=tx_id))
    
    return results


@update
def icrc37_revoke_collection_approvals(args: Vec[RevokeCollectionApprovalArg]) -> Vec[Opt[RevokeCollectionApprovalResult]]:
    """Revoke collection-level approvals."""
    caller = ic.caller()
    results = []
    
    for arg in args:
        caller_account = Account(
            owner=caller,
            subaccount=arg.get("from_subaccount")
        )
        
        spender = arg.get("spender")
        if spender:
            # Revoke specific collection approval
            approval_id = _get_approval_id("collection", 0, caller_account, spender)
            approval = NFTApproval[approval_id]
            if not approval:
                results.append(RevokeCollectionApprovalResult(Err=RevokeCollectionApprovalError(ApprovalDoesNotExist=null)))
                continue
            approval.delete()
        else:
            # Revoke all collection approvals for this owner
            all_approvals = NFTApproval.instances()
            owner_sub = _subaccount_to_hex(arg.get("from_subaccount"))
            for approval in all_approvals:
                if approval.approval_type == "collection":
                    if approval.owner_principal == caller.to_str() and approval.owner_subaccount == owner_sub:
                        approval.delete()
        
        tx_id = _log_transaction(
            kind="revoke_collection",
            token_id=0,
            from_principal=caller.to_str()
        )
        
        logger.info(f"Revoke collection approval")
        results.append(RevokeCollectionApprovalResult(Ok=tx_id))
    
    return results


@update
def icrc37_transfer_from(args: Vec[TransferFromArg]) -> Vec[Opt[TransferFromResult]]:
    """Transfer NFTs on behalf of the owner (if approved)."""
    caller = ic.caller()
    results = []
    
    for arg in args:
        token = _get_token(arg["token_id"])
        
        if not token:
            results.append(TransferFromResult(Err=TransferFromError(NonExistingTokenId=null)))
            continue
        
        # Frozen tokens cannot be transferred via approvals
        if _is_token_frozen(token):
            results.append(TransferFromResult(Err=TransferFromError(
                GenericError=GenericError(error_code=423, message="Token is frozen by the registry authority")
            )))
            continue
        
        from_account = arg["from_"]
        
        # Check that from_account is the actual owner
        if not _is_owner(token, from_account):
            results.append(TransferFromResult(Err=TransferFromError(Unauthorized=null)))
            continue
        
        # Build spender account (caller)
        spender_account = Account(
            owner=caller,
            subaccount=arg.get("spender_subaccount")
        )
        
        # Check approval (unless caller is owner)
        if not _is_owner(token, spender_account) and not _is_approved(token, spender_account):
            results.append(TransferFromResult(Err=TransferFromError(Unauthorized=null)))
            continue
        
        # Check recipient is not the same as sender
        to_account = arg["to"]
        if _is_owner(token, to_account):
            results.append(TransferFromResult(Err=TransferFromError(InvalidRecipient=null)))
            continue
        
        # Perform transfer
        old_owner = token.owner_principal
        old_subaccount = token.owner_subaccount
        
        token.owner_principal = to_account["owner"].to_str()
        token.owner_subaccount = _subaccount_to_hex(to_account.get("subaccount"))
        
        # Clear token-level approvals for this token
        all_approvals = NFTApproval.instances()
        for approval in all_approvals:
            if approval.approval_type == "token" and approval.token_id == int(arg["token_id"]):
                approval.delete()
        
        # Log transaction
        memo = arg.get("memo")
        tx_id = _log_transaction(
            kind="transfer_from",
            token_id=int(arg["token_id"]),
            from_principal=old_owner,
            from_subaccount=old_subaccount,
            to_principal=token.owner_principal,
            to_subaccount=token.owner_subaccount,
            spender_principal=caller.to_str(),
            spender_subaccount=_subaccount_to_hex(arg.get("spender_subaccount")),
            memo=memo.hex() if memo else ""
        )
        
        logger.info(f"Transfer_from: token {arg['token_id']} by {caller.to_str()}")
        results.append(TransferFromResult(Ok=tx_id))
    
    return results


# =============================================================================
# Admin / Test Methods
# =============================================================================

@update
def mint(arg: MintArg) -> MintResult:
    """Mint a new NFT. Allowed in test mode or for authorized minter principals."""
    caller = ic.caller()
    collection = _get_collection()

    if not _can_mint(caller):
        return MintResult(Err=MintError(Unauthorized=null))
    
    # Check supply cap
    if collection.supply_cap > 0 and collection.total_supply >= collection.supply_cap:
        return MintResult(Err=MintError(SupplyCapReached=null))
    
    # Determine the token ID. If the caller did not specify one, auto-assign
    # the next sequential ID from the collection counter.
    requested_token_id = arg.get("token_id")
    if requested_token_id is None:
        _ensure_next_token_id(collection)
        token_id = collection.next_token_id
        collection.next_token_id = token_id + 1
    else:
        token_id = int(requested_token_id)
        # Keep the counter ahead of any explicitly chosen ID.
        if collection.next_token_id <= token_id:
            collection.next_token_id = token_id + 1

    # Check token ID doesn't exist
    existing = _get_token(token_id)
    if existing:
        return MintResult(Err=MintError(TokenIdAlreadyExists=null))

    # Convert metadata to JSON
    import json
    metadata_dict = {}
    if arg.get("metadata"):
        for key, value in arg["metadata"]:
            if "Text" in value:
                metadata_dict[key] = value["Text"]
            elif "Nat" in value:
                metadata_dict[key] = value["Nat"]
            elif "Int" in value:
                metadata_dict[key] = value["Int"]

    # Create token. The minting caller becomes the token's registry
    # authority (may force-transfer/freeze it later).
    owner = arg["owner"]
    token = NFTToken(
        id=token_id,
        owner_principal=owner["owner"].to_str(),
        owner_subaccount=_subaccount_to_hex(owner.get("subaccount")),
        metadata_json=json.dumps(metadata_dict),
        authority_principal=caller.to_str(),
        frozen=0
    )

    # Update supply
    collection.total_supply += 1

    # Log transaction
    tx_id = _log_transaction(
        kind="mint",
        token_id=token_id,
        to_principal=owner["owner"].to_str(),
        to_subaccount=_subaccount_to_hex(owner.get("subaccount"))
    )

    logger.info(f"Mint: token {token_id} to {owner['owner'].to_str()}")
    return MintResult(Ok=token_id)


# =============================================================================
# Authority-Controlled Operations (registry override)
# =============================================================================

@update
def force_transfer(arg: ForceTransferArg) -> AuthorityResult:
    """Forcefully transfer a token to a new owner, bypassing holder consent.

    Only the token's registry authority (the principal that minted it, still
    an authorized minter) or a canister controller may call this. Works on
    frozen tokens. Clears existing token-level approvals. Intended for
    judicial procedures, governance decisions, and key recovery.
    """
    caller = ic.caller()
    token = _get_token(arg["token_id"])
    if not token:
        return AuthorityResult(Err=AuthorityError(NonExistingTokenId=null))

    if not _is_token_authority(caller, token):
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    to_account = arg["to"]
    if _is_owner(token, to_account):
        return AuthorityResult(Err=AuthorityError(InvalidRecipient=null))

    old_owner = token.owner_principal
    old_subaccount = token.owner_subaccount

    token.owner_principal = to_account["owner"].to_str()
    token.owner_subaccount = _subaccount_to_hex(to_account.get("subaccount"))

    # Clear token-level approvals granted by the previous owner
    for approval in NFTApproval.instances():
        if approval.approval_type == "token" and approval.token_id == int(arg["token_id"]):
            approval.delete()

    memo = arg.get("memo") or ""
    tx_id = _log_transaction(
        kind="force_transfer",
        token_id=int(arg["token_id"]),
        from_principal=old_owner,
        from_subaccount=old_subaccount,
        to_principal=token.owner_principal,
        to_subaccount=token.owner_subaccount,
        spender_principal=caller.to_str(),
        memo=memo[:512]
    )

    logger.info(
        f"Force transfer: token {arg['token_id']} from {old_owner} to "
        f"{token.owner_principal} by authority {caller.to_str()}"
    )
    return AuthorityResult(Ok=tx_id)


@update
def freeze_token(arg: FreezeArg) -> AuthorityResult:
    """Freeze a token: holders cannot transfer it until unfrozen.

    Only the token's registry authority or a canister controller may call
    this. force_transfer still works on frozen tokens.
    """
    caller = ic.caller()
    token = _get_token(arg["token_id"])
    if not token:
        return AuthorityResult(Err=AuthorityError(NonExistingTokenId=null))

    if not _is_token_authority(caller, token):
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    reason = arg.get("reason") or ""
    token.frozen = 1
    token.frozen_reason = reason[:512]

    tx_id = _log_transaction(
        kind="freeze",
        token_id=int(arg["token_id"]),
        spender_principal=caller.to_str(),
        memo=reason[:512]
    )
    logger.info(f"Freeze: token {arg['token_id']} by authority {caller.to_str()}")
    return AuthorityResult(Ok=tx_id)


@update
def unfreeze_token(token_id: nat) -> AuthorityResult:
    """Unfreeze a token, restoring normal holder transfers."""
    caller = ic.caller()
    token = _get_token(token_id)
    if not token:
        return AuthorityResult(Err=AuthorityError(NonExistingTokenId=null))

    if not _is_token_authority(caller, token):
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    token.frozen = 0
    token.frozen_reason = ""

    tx_id = _log_transaction(
        kind="unfreeze",
        token_id=int(token_id),
        spender_principal=caller.to_str()
    )
    logger.info(f"Unfreeze: token {token_id} by authority {caller.to_str()}")
    return AuthorityResult(Ok=tx_id)


@update
def transfer_authority(arg: TransferAuthorityArg) -> AuthorityResult:
    """Hand over the registry authority of a token to another principal.

    ERC-6147-style guard change: only the token's current authority (still an
    authorized minter) or a canister controller may call this. The new
    authority gains force_transfer/freeze/unfreeze rights over the token
    (provided it is, or becomes, an authorized minter).
    """
    caller = ic.caller()
    token = _get_token(arg["token_id"])
    if not token:
        return AuthorityResult(Err=AuthorityError(NonExistingTokenId=null))

    if not _is_token_authority(caller, token):
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    old_authority = getattr(token, "authority_principal", "") or ""
    new_authority = arg["new_authority"].to_str()
    if new_authority == old_authority:
        return AuthorityResult(Err=AuthorityError(InvalidRecipient=null))

    token.authority_principal = new_authority

    memo = arg.get("memo") or ""
    tx_id = _log_transaction(
        kind="transfer_authority",
        token_id=int(arg["token_id"]),
        from_principal=old_authority,
        to_principal=new_authority,
        spender_principal=caller.to_str(),
        memo=memo[:512]
    )
    logger.info(
        f"Authority transfer: token {arg['token_id']} authority "
        f"{old_authority} -> {new_authority} by {caller.to_str()}"
    )
    return AuthorityResult(Ok=tx_id)


@query
def is_token_frozen(token_id: nat) -> bool:
    """Check whether a token is currently frozen."""
    token = _get_token(token_id)
    if not token:
        return False
    return _is_token_frozen(token)


@query
def get_token_authority(token_id: nat) -> Opt[text]:
    """Return the registry authority principal for a token, if any."""
    token = _get_token(token_id)
    if not token:
        return None
    authority = getattr(token, "authority_principal", "") or ""
    return authority if authority else None


@query
def icrc7_supported_standards() -> Vec[StandardRecord]:
    """Returns the list of standards supported by this canister."""
    return [
        StandardRecord(name="ICRC-7", url="https://github.com/dfinity/ICRC/blob/main/ICRCs/ICRC-7/ICRC-7.md"),
        StandardRecord(name="ICRC-37", url="https://github.com/dfinity/ICRC/blob/main/ICRCs/ICRC-37/ICRC-37.md"),
    ]


@query
def get_transactions(start: nat, length: nat) -> Vec[TransactionRecord]:
    """Get transaction history (for debugging/indexer)."""
    all_txs = NFTTransactionLog.instances()
    sorted_txs = sorted(all_txs, key=lambda x: x.id)
    result = []
    for tx in sorted_txs[int(start):int(start) + int(length)]:
        result.append(TransactionRecord(
            id=tx.id,
            kind=tx.kind,
            timestamp=tx.timestamp,
            token_id=tx.token_id,
            from_principal=tx.from_principal,
            from_subaccount=tx.from_subaccount,
            to_principal=tx.to_principal,
            to_subaccount=tx.to_subaccount,
            spender_principal=tx.spender_principal,
            spender_subaccount=tx.spender_subaccount,
            memo=tx.memo
        ))
    return result


@query
def is_test_mode() -> bool:
    """Check if the collection is in test mode."""
    collection = NFTCollection["config"]
    if collection:
        return collection.test_mode == 1
    return False


@query
def list_authorized_minters() -> Vec[text]:
    """Return principals authorized to mint when not in test mode."""
    try:
        return sorted(_authorized_minter_set())
    except Exception:
        return []


@update
def add_authorized_minter(principal: text) -> text:
    """Add a principal allowed to mint (controller-only)."""
    import json

    caller = ic.caller()
    if not ic.is_controller(caller):
        return json.dumps({"success": False, "error": "Only canister controllers may authorize minters"})

    principal = (principal or "").strip()
    if not principal:
        return json.dumps({"success": False, "error": "principal is required"})

    collection = _get_collection()
    current = _authorized_minter_set()
    if principal in current:
        return json.dumps({"success": True, "message": "Principal already authorized", "minters": sorted(current)})

    current.add(principal)
    collection.authorized_minters = ",".join(sorted(current))
    logger.info(f"Authorized minter added: {principal}")
    return json.dumps({"success": True, "minters": sorted(current)})


@update
def remove_authorized_minter(principal: text) -> text:
    """Remove a mint-authorized principal (controller-only)."""
    import json

    caller = ic.caller()
    if not ic.is_controller(caller):
        return json.dumps({"success": False, "error": "Only canister controllers may revoke minters"})

    principal = (principal or "").strip()
    collection = _get_collection()
    current = _authorized_minter_set()
    if principal not in current:
        return json.dumps({"success": False, "error": "Principal not in authorized minters list"})

    current.discard(principal)
    collection.authorized_minters = ",".join(sorted(current))
    logger.info(f"Authorized minter removed: {principal}")
    return json.dumps({"success": True, "minters": sorted(current)})
