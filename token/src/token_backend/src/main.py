from basilisk import (
    Opt,
    Principal,
    Record,
    StableBTreeMap,
    Tuple,
    Variant,
    Vec,
    blob,
    ic,
    init,
    nat,
    nat8,
    null,
    query,
    text,
    update,
    void,
)
from ic_python_db import Database, Entity, Integer, String
from ic_python_logging import get_logger

# Initialize stable storage for the database
storage = StableBTreeMap[str, str](
    memory_id=1, max_key_size=200, max_value_size=100_000
)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("token")


# Database Entity for storing balances
class TokenBalance(Entity):
    __alias__ = "id"
    id = String()
    amount = Integer()


# Database Entity for storing token metadata
class TokenConfig(Entity):
    __alias__ = "key"
    key = String()
    value = String()


# Database Entity for frozen accounts (ERC-3643-style address freeze)
class FrozenAccount(Entity):
    __alias__ = "id"
    id = String()  # Account key ("principal:subaccount_hex_or_default")
    reason = String(max_length=512, default="")


# Database Entity for transaction log (for indexer functionality)
class TransactionLog(Entity):
    __alias__ = "id"
    id = Integer()  # Block index / transaction ID
    kind = String()  # "transfer", "mint", "burn"
    timestamp = Integer()  # Nanoseconds since epoch
    from_owner = String()  # Sender principal (empty for mint)
    from_subaccount = String()  # Hex-encoded subaccount or empty
    to_owner = String()  # Recipient principal
    to_subaccount = String()  # Hex-encoded subaccount or empty
    amount = Integer()
    fee = Integer()
    memo = String()  # Hex-encoded memo or empty


# Register entity types
Database.get_instance().register_entity_type(TokenBalance)
Database.get_instance().register_entity_type(TokenConfig)
Database.get_instance().register_entity_type(FrozenAccount)
Database.get_instance().register_entity_type(TransactionLog)


# ICRC-1 Types
MetadataEntry = Tuple[text, text]


class Account(Record):
    owner: Principal
    subaccount: Opt[blob]


class TransferArgs(Record):
    from_subaccount: Opt[blob]
    to: Account
    amount: nat
    fee: Opt[nat]
    memo: Opt[blob]
    created_at_time: Opt[nat]


class TransferResult(Record):
    success: bool
    block_index: Opt[nat]
    error: Opt[text]


class MintArgs(Record):
    to: Account
    amount: nat


class MintResult(Record):
    success: bool
    new_balance: Opt[nat]
    error: Opt[text]
    block_index: Opt[nat]


class TestTransferArgs(Record):
    from_owner: text
    to: Account
    amount: nat


class TokenMetadataRecord(Record):
    name: text
    symbol: text
    decimals: nat8
    fee: nat
    total_supply: nat


class UpdateMetadataArgs(Record):
    name: text
    symbol: text


class UpdateMetadataResult(Record):
    success: bool
    error: Opt[text]
    name: text
    symbol: text


class InitArgs(Record):
    name: text
    symbol: text
    decimals: nat8
    total_supply: nat
    fee: nat
    test: Opt[bool]
    # When set, this principal (instead of the installing caller) becomes the
    # ledger owner/authority and receives the initial supply. Used by
    # orchestrators (e.g. Casals) that install on behalf of a realm backend.
    initial_owner: Opt[Principal]


# Authority-controlled operations (ERC-3643/T-REX-style semantics).
# The ledger authority (defaults to the owner) or a canister controller can
# force-transfer funds, freeze/unfreeze accounts, and hand over the authority.
class ForcedTransferArgs(Record):
    from_: Account
    to: Account
    amount: nat
    memo: Opt[text]


class FreezeAccountArgs(Record):
    account: Account
    reason: Opt[text]


class TransferAuthorityArgs(Record):
    new_authority: Principal
    memo: Opt[text]


class AuthorityError(Variant, total=False):
    Unauthorized: null
    InsufficientBalance: null
    InvalidRecipient: null
    GenericError: text


class AuthorityResult(Variant, total=False):
    Ok: nat
    Err: AuthorityError


class FrozenStatus(Record):
    frozen: bool
    reason: text


class HolderInfo(Record):
    address: text
    balance: nat


class TokenDistribution(Record):
    holders: Vec["HolderInfo"]
    total_supply: nat
    holder_count: nat


# Token configuration defaults. Actual values come from the install args and
# are persisted in TokenConfig; these are fallbacks for legacy deployments
# that were installed before metadata was config-backed.
DEFAULT_TOKEN_NAME = "Simple Token"
DEFAULT_TOKEN_SYMBOL = "SMPL"
DEFAULT_TOKEN_DECIMALS = 8
DEFAULT_TOKEN_FEE = 10_000


class MetadataHelper:
    @staticmethod
    def _get(key, default):
        config = TokenConfig[key]
        if config and config.value:
            return config.value
        return default

    @staticmethod
    def set(key, value):
        config = TokenConfig[key]
        if config:
            config.value = str(value)
        else:
            TokenConfig(key=key, value=str(value))

    @staticmethod
    def get_name():
        return MetadataHelper._get("name", DEFAULT_TOKEN_NAME)

    @staticmethod
    def get_symbol():
        return MetadataHelper._get("symbol", DEFAULT_TOKEN_SYMBOL)

    @staticmethod
    def get_decimals():
        return int(MetadataHelper._get("decimals", DEFAULT_TOKEN_DECIMALS))

    @staticmethod
    def get_fee():
        return int(MetadataHelper._get("fee", DEFAULT_TOKEN_FEE))


def _validate_metadata(name: str, symbol: str):
    """Return (name, symbol, error) after normalizing user input."""
    clean_name = (name or "").strip()
    clean_symbol = (symbol or "").strip().upper()
    if not clean_name or len(clean_name) > 64:
        return None, None, "name must be 1-64 characters"
    if not clean_symbol or len(clean_symbol) > 16:
        return None, None, "symbol must be 1-16 characters"
    if not all(ch.isalnum() or ch == "_" for ch in clean_symbol):
        return None, None, "symbol must be alphanumeric (underscore allowed)"
    return clean_name, clean_symbol, None


class TokenHelper:
    @staticmethod
    def get_account_key(owner, subaccount=None):
        sub = subaccount.hex() if subaccount else "default"
        return f"{owner}:{sub}"

    @staticmethod
    def get_balance(owner, subaccount=None):
        key = TokenHelper.get_account_key(owner, subaccount)
        balance = TokenBalance[key]
        if balance:
            return balance.amount or 0
        return 0

    @staticmethod
    def set_balance(owner, balance_amount, subaccount=None):
        key = TokenHelper.get_account_key(owner, subaccount)
        balance = TokenBalance[key]
        if balance:
            balance.amount = balance_amount
        else:
            TokenBalance(id=key, amount=balance_amount)

    @staticmethod
    def get_total_supply():
        config = TokenConfig["total_supply"]
        if config and config.value:
            return int(config.value)
        return 0

    @staticmethod
    def set_total_supply(supply):
        config = TokenConfig["total_supply"]
        if config:
            config.value = str(supply)
        else:
            TokenConfig(key="total_supply", value=str(supply))


class OwnerHelper:
    @staticmethod
    def get_owner():
        config = TokenConfig["owner"]
        if config and config.value:
            return config.value
        return None

    @staticmethod
    def set_owner(owner):
        config = TokenConfig["owner"]
        if config:
            config.value = owner
        else:
            TokenConfig(key="owner", value=owner)

    @staticmethod
    def is_owner(principal):
        return principal == OwnerHelper.get_owner()


class AuthorityHelper:
    """Ledger authority for ERC-3643-style operations.

    Defaults to the owner (deployer) until explicitly handed over via
    transfer_authority. Canister controllers always retain authority powers.
    """

    @staticmethod
    def get_authority():
        config = TokenConfig["authority"]
        if config and config.value:
            return config.value
        return OwnerHelper.get_owner()

    @staticmethod
    def set_authority(authority):
        config = TokenConfig["authority"]
        if config:
            config.value = authority
        else:
            TokenConfig(key="authority", value=authority)

    @staticmethod
    def is_authority(caller_principal) -> bool:
        if ic.is_controller(caller_principal):
            return True
        return caller_principal.to_str() == AuthorityHelper.get_authority()


class FreezeHelper:
    @staticmethod
    def freeze(owner, subaccount=None, reason=""):
        key = TokenHelper.get_account_key(owner, subaccount)
        entry = FrozenAccount[key]
        if entry:
            entry.reason = reason[:512]
        else:
            FrozenAccount(id=key, reason=reason[:512])

    @staticmethod
    def unfreeze(owner, subaccount=None):
        key = TokenHelper.get_account_key(owner, subaccount)
        entry = FrozenAccount[key]
        if entry:
            entry.delete()

    @staticmethod
    def get_frozen(owner, subaccount=None):
        """Return the FrozenAccount entry, or None if not frozen."""
        key = TokenHelper.get_account_key(owner, subaccount)
        return FrozenAccount[key]


class TransactionHelper:
    @staticmethod
    def get_next_block_index():
        config = TokenConfig["next_block_index"]
        if config and config.value:
            return int(config.value)
        return 0

    @staticmethod
    def increment_block_index():
        current = TransactionHelper.get_next_block_index()
        config = TokenConfig["next_block_index"]
        if config:
            config.value = str(current + 1)
        else:
            TokenConfig(key="next_block_index", value=str(current + 1))
        return current

    @staticmethod
    def log_transaction(
        kind: str,
        from_owner: str,
        from_subaccount: bytes,
        to_owner: str,
        to_subaccount: bytes,
        amount: int,
        fee: int,
        memo: bytes = None,
    ) -> int:
        """Log a transaction and return its block index."""
        block_index = TransactionHelper.increment_block_index()
        timestamp = ic.time()  # Nanoseconds since epoch

        TransactionLog(
            id=block_index,
            kind=kind,
            timestamp=timestamp,
            from_owner=from_owner or "",
            from_subaccount=from_subaccount.hex() if from_subaccount else "",
            to_owner=to_owner,
            to_subaccount=to_subaccount.hex() if to_subaccount else "",
            amount=amount,
            fee=fee,
            memo=memo.hex() if memo else "",
        )

        logger.info(f"Logged {kind} transaction #{block_index}: {amount} tokens")
        return block_index

    @staticmethod
    def get_transactions_for_account(
        owner: str, subaccount: bytes = None, start: int = None, max_results: int = 20
    ):
        """Get transactions involving a specific account."""
        sub_hex = subaccount.hex() if subaccount else ""
        transactions = []

        # Get all transactions and filter by account
        all_txs = list(TransactionLog.instances())

        # Filter transactions where account is sender or receiver
        for tx in all_txs:
            is_sender = tx.from_owner == owner and tx.from_subaccount == sub_hex
            is_receiver = tx.to_owner == owner and tx.to_subaccount == sub_hex

            if is_sender or is_receiver:
                # If start is specified, only include transactions with id < start
                if start is not None and tx.id >= start:
                    continue
                transactions.append(tx)

        # Sort by id descending (newest first)
        transactions.sort(key=lambda x: x.id, reverse=True)

        # Apply max_results limit
        return transactions[:max_results]


@init
def init_(args: InitArgs) -> void:
    logger.info("Initializing token canister")
    initial_owner = args.get("initial_owner")
    deployer = initial_owner.to_str() if initial_owner else ic.caller().to_str()
    OwnerHelper.set_owner(deployer)
    MetadataHelper.set("name", args["name"])
    MetadataHelper.set("symbol", args["symbol"])
    MetadataHelper.set("decimals", args["decimals"])
    MetadataHelper.set("fee", args["fee"])
    TokenHelper.set_balance(deployer, args["total_supply"])
    TokenHelper.set_total_supply(args["total_supply"])
    if args.get("test"):
        TokenConfig(key="test", value="true")
        logger.info("Test mode enabled - public minting allowed")
    logger.info(f"Token initialized. Supply: {args['total_supply']} to {deployer}")


@query
def icrc1_name() -> text:
    return MetadataHelper.get_name()


@query
def icrc1_symbol() -> text:
    return MetadataHelper.get_symbol()


@query
def icrc1_decimals() -> nat8:
    return MetadataHelper.get_decimals()


@query
def icrc1_fee() -> nat:
    return MetadataHelper.get_fee()


@query
def icrc1_total_supply() -> nat:
    return TokenHelper.get_total_supply()


@query
def icrc1_minting_account() -> Opt[Account]:
    return None


@query
def icrc1_balance_of(account: Account) -> nat:
    owner_str = account["owner"].to_str()
    return TokenHelper.get_balance(owner_str, account.get("subaccount"))


@query
def icrc1_metadata() -> Vec[MetadataEntry]:
    return [
        ("icrc1:name", MetadataHelper.get_name()),
        ("icrc1:symbol", MetadataHelper.get_symbol()),
        ("icrc1:decimals", str(MetadataHelper.get_decimals())),
        ("icrc1:fee", str(MetadataHelper.get_fee())),
    ]


@query
def icrc1_supported_standards() -> Vec[MetadataEntry]:
    return [
        ("ICRC-1", "https://github.com/dfinity/ICRC-1"),
    ]


@update
def icrc1_transfer(args: TransferArgs) -> TransferResult:
    caller = ic.caller().to_str()
    logger.info(
        f"Transfer request: {caller} -> {args['to']['owner'].to_str()}, amount: {args['amount']}"
    )
    fee = args.get("fee") if args.get("fee") is not None else MetadataHelper.get_fee()
    return _execute_transfer(
        caller,
        args.get("from_subaccount"),
        args["to"],
        args["amount"],
        fee,
        args.get("memo"),
    )


def _execute_transfer(
    from_owner: str,
    from_subaccount,
    to_account: Account,
    amount: nat,
    fee: nat,
    memo,
) -> TransferResult:
    frozen = FreezeHelper.get_frozen(from_owner, from_subaccount)
    if frozen:
        logger.warning(f"Transfer blocked: account {from_owner} is frozen")
        return TransferResult(
            success=False,
            block_index=None,
            error="Account is frozen by the ledger authority",
        )

    sender_balance = TokenHelper.get_balance(from_owner, from_subaccount)
    total_deduction = amount + fee

    if sender_balance < total_deduction:
        logger.warning(f"Insufficient balance: {sender_balance} < {total_deduction}")
        return TransferResult(
            success=False,
            block_index=None,
            error=f"Insufficient balance. Have {sender_balance}, need {total_deduction}",
        )

    recipient = to_account["owner"].to_str()
    if recipient == from_owner and not from_subaccount and not to_account.get("subaccount"):
        return TransferResult(
            success=False,
            block_index=None,
            error="Sender and recipient must differ",
        )

    recipient_balance = TokenHelper.get_balance(recipient, to_account.get("subaccount"))

    TokenHelper.set_balance(
        from_owner, sender_balance - total_deduction, from_subaccount
    )
    TokenHelper.set_balance(
        recipient, recipient_balance + amount, to_account.get("subaccount")
    )

    current_supply = TokenHelper.get_total_supply()
    TokenHelper.set_total_supply(current_supply - fee)

    block_index = TransactionHelper.log_transaction(
        kind="transfer",
        from_owner=from_owner,
        from_subaccount=from_subaccount,
        to_owner=recipient,
        to_subaccount=to_account.get("subaccount"),
        amount=amount,
        fee=fee,
        memo=memo,
    )

    logger.info(
        f"Transfer successful: {amount} tokens {from_owner} -> {recipient}, block_index={block_index}"
    )

    return TransferResult(success=True, block_index=block_index, error=None)


@update
def test_transfer(args: TestTransferArgs) -> TransferResult:
    """Transfer from any principal — test mode only (no caller authentication)."""
    if not _is_test_mode():
        return TransferResult(
            success=False,
            block_index=None,
            error="test_transfer is only available in test mode",
        )

    from_owner = (args.get("from_owner") or "").strip()
    if not from_owner:
        return TransferResult(
            success=False,
            block_index=None,
            error="from_owner is required",
        )

    logger.info(
        f"Test transfer: {from_owner} -> {args['to']['owner'].to_str()}, amount: {args['amount']}"
    )
    return _execute_transfer(
        from_owner,
        None,
        args["to"],
        args["amount"],
        MetadataHelper.get_fee(),
        None,
    )


@update
def mint(args: MintArgs) -> MintResult:
    caller = ic.caller().to_str()
    logger.info(
        f"Mint request from {caller}: {args['amount']} to {args['to']['owner'].to_str()}"
    )

    if not OwnerHelper.is_owner(caller) and not _is_test_mode():
        logger.warning(f"Unauthorized mint attempt by {caller}")
        return MintResult(
            success=False,
            new_balance=None,
            error="Only the token owner can mint tokens",
            block_index=None,
        )

    recipient = args["to"]["owner"].to_str()
    current_balance = TokenHelper.get_balance(recipient, args["to"].get("subaccount"))
    new_balance = current_balance + args["amount"]

    TokenHelper.set_balance(recipient, new_balance, args["to"].get("subaccount"))

    current_supply = TokenHelper.get_total_supply()
    TokenHelper.set_total_supply(current_supply + args["amount"])

    # Log the mint transaction for indexer
    block_index = TransactionHelper.log_transaction(
        kind="mint",
        from_owner="",  # No sender for mints
        from_subaccount=None,
        to_owner=recipient,
        to_subaccount=args["to"].get("subaccount"),
        amount=args["amount"],
        fee=0,
        memo=None,
    )

    logger.info(
        f"Minted {args['amount']} tokens to {recipient}. New balance: {new_balance}, block_index={block_index}"
    )

    return MintResult(
        success=True, new_balance=new_balance, error=None, block_index=block_index
    )


# ============================================================================
# Authority-Controlled Operations (ERC-3643-style ledger authority)
# ============================================================================


@update
def forced_transfer(args: ForcedTransferArgs) -> AuthorityResult:
    """Forcefully move tokens between accounts, bypassing holder consent.

    Only the ledger authority or a canister controller may call this. Works
    on frozen accounts and charges no fee. Intended for judicial procedures,
    governance decisions, and key recovery (ERC-3643 forcedTransfer).
    """
    caller = ic.caller()
    if not AuthorityHelper.is_authority(caller):
        logger.warning(f"Unauthorized forced_transfer attempt by {caller.to_str()}")
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    from_account = args["from_"]
    to_account = args["to"]
    from_owner = from_account["owner"].to_str()
    to_owner = to_account["owner"].to_str()
    from_sub = from_account.get("subaccount")
    to_sub = to_account.get("subaccount")
    amount = args["amount"]

    if from_owner == to_owner and (from_sub or None) == (to_sub or None):
        return AuthorityResult(Err=AuthorityError(InvalidRecipient=null))

    from_balance = TokenHelper.get_balance(from_owner, from_sub)
    if from_balance < amount:
        logger.warning(
            f"forced_transfer: insufficient balance {from_balance} < {amount}"
        )
        return AuthorityResult(Err=AuthorityError(InsufficientBalance=null))

    to_balance = TokenHelper.get_balance(to_owner, to_sub)
    TokenHelper.set_balance(from_owner, from_balance - amount, from_sub)
    TokenHelper.set_balance(to_owner, to_balance + amount, to_sub)

    memo = args.get("memo") or ""
    block_index = TransactionHelper.log_transaction(
        kind="forced_transfer",
        from_owner=from_owner,
        from_subaccount=from_sub,
        to_owner=to_owner,
        to_subaccount=to_sub,
        amount=amount,
        fee=0,
        memo=memo.encode() if memo else None,
    )

    logger.info(
        f"Forced transfer: {amount} tokens {from_owner} -> {to_owner} "
        f"by authority {caller.to_str()}, block_index={block_index}"
    )
    return AuthorityResult(Ok=block_index)


@update
def freeze_account(args: FreezeAccountArgs) -> AuthorityResult:
    """Freeze an account: it cannot send tokens until unfrozen.

    Only the ledger authority or a canister controller may call this.
    Receiving tokens and forced_transfer remain possible on frozen accounts.
    """
    caller = ic.caller()
    if not AuthorityHelper.is_authority(caller):
        logger.warning(f"Unauthorized freeze_account attempt by {caller.to_str()}")
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    account = args["account"]
    owner = account["owner"].to_str()
    subaccount = account.get("subaccount")
    reason = args.get("reason") or ""

    FreezeHelper.freeze(owner, subaccount, reason)

    block_index = TransactionHelper.log_transaction(
        kind="freeze",
        from_owner=owner,
        from_subaccount=subaccount,
        to_owner="",
        to_subaccount=None,
        amount=0,
        fee=0,
        memo=reason.encode() if reason else None,
    )
    logger.info(f"Account frozen: {owner} by authority {caller.to_str()}")
    return AuthorityResult(Ok=block_index)


@update
def unfreeze_account(account: Account) -> AuthorityResult:
    """Unfreeze an account, restoring normal transfers."""
    caller = ic.caller()
    if not AuthorityHelper.is_authority(caller):
        logger.warning(f"Unauthorized unfreeze_account attempt by {caller.to_str()}")
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    owner = account["owner"].to_str()
    subaccount = account.get("subaccount")

    FreezeHelper.unfreeze(owner, subaccount)

    block_index = TransactionHelper.log_transaction(
        kind="unfreeze",
        from_owner=owner,
        from_subaccount=subaccount,
        to_owner="",
        to_subaccount=None,
        amount=0,
        fee=0,
        memo=None,
    )
    logger.info(f"Account unfrozen: {owner} by authority {caller.to_str()}")
    return AuthorityResult(Ok=block_index)


@update
def transfer_authority(args: TransferAuthorityArgs) -> AuthorityResult:
    """Hand over the ledger authority to another principal.

    Only the current authority or a canister controller may call this.
    """
    caller = ic.caller()
    if not AuthorityHelper.is_authority(caller):
        logger.warning(
            f"Unauthorized transfer_authority attempt by {caller.to_str()}"
        )
        return AuthorityResult(Err=AuthorityError(Unauthorized=null))

    old_authority = AuthorityHelper.get_authority() or ""
    new_authority = args["new_authority"].to_str()
    if new_authority == old_authority:
        return AuthorityResult(Err=AuthorityError(InvalidRecipient=null))

    AuthorityHelper.set_authority(new_authority)

    memo = args.get("memo") or ""
    block_index = TransactionHelper.log_transaction(
        kind="transfer_authority",
        from_owner=old_authority,
        from_subaccount=None,
        to_owner=new_authority,
        to_subaccount=None,
        amount=0,
        fee=0,
        memo=memo.encode() if memo else None,
    )
    logger.info(
        f"Authority transfer: {old_authority} -> {new_authority} "
        f"by {caller.to_str()}"
    )
    return AuthorityResult(Ok=block_index)


@query
def is_account_frozen(account: Account) -> FrozenStatus:
    """Check whether an account is currently frozen (and why)."""
    owner = account["owner"].to_str()
    entry = FreezeHelper.get_frozen(owner, account.get("subaccount"))
    if entry:
        return FrozenStatus(frozen=True, reason=entry.reason or "")
    return FrozenStatus(frozen=False, reason="")


@query
def get_authority() -> text:
    """Return the current ledger authority principal."""
    authority = AuthorityHelper.get_authority()
    return authority if authority else ""


@query
def get_owner() -> text:
    owner = OwnerHelper.get_owner()
    return owner if owner else ""


@query
def can_manage_token() -> bool:
    """True when the caller can update token metadata."""
    if _is_test_mode():
        return True
    caller = ic.caller()
    if OwnerHelper.is_owner(caller.to_str()):
        return True
    return AuthorityHelper.is_authority(caller)


@update
def update_token_metadata(args: UpdateMetadataArgs) -> UpdateMetadataResult:
    """Update display name and ticker symbol (owner, authority, or test mode)."""
    caller = ic.caller()
    if (
        not _is_test_mode()
        and not OwnerHelper.is_owner(caller.to_str())
        and not AuthorityHelper.is_authority(caller)
    ):
        return UpdateMetadataResult(
            success=False,
            error="Only the token owner or ledger authority can update metadata",
            name=MetadataHelper.get_name(),
            symbol=MetadataHelper.get_symbol(),
        )

    name, symbol, err = _validate_metadata(args.get("name"), args.get("symbol"))
    if err:
        return UpdateMetadataResult(
            success=False,
            error=err,
            name=MetadataHelper.get_name(),
            symbol=MetadataHelper.get_symbol(),
        )

    MetadataHelper.set("name", name)
    MetadataHelper.set("symbol", symbol)
    logger.info(
        f"Token metadata updated by {caller.to_str()}: name={name}, symbol={symbol}"
    )
    return UpdateMetadataResult(
        success=True, error=None, name=name, symbol=symbol
    )


@query
def get_token_info() -> TokenMetadataRecord:
    return TokenMetadataRecord(
        name=MetadataHelper.get_name(),
        symbol=MetadataHelper.get_symbol(),
        decimals=MetadataHelper.get_decimals(),
        fee=MetadataHelper.get_fee(),
        total_supply=TokenHelper.get_total_supply(),
    )


@query
def get_my_balance() -> nat:
    return TokenHelper.get_balance(ic.caller().to_str())


@query
def get_my_principal() -> text:
    return ic.caller().to_str()


def _is_test_mode() -> bool:
    config = TokenConfig["test"]
    return config is not None and config.value == "true"


@query
def is_test_mode() -> bool:
    return _is_test_mode()


@query
def get_token_distribution() -> TokenDistribution:
    """Get all token holders and their balances for distribution visualization."""
    holders = []

    for balance in TokenBalance.instances():
        if balance.amount and balance.amount > 0:
            holders.append(HolderInfo(address=balance.id, balance=balance.amount))

    # Sort by balance descending
    holders.sort(key=lambda h: h["balance"], reverse=True)

    return TokenDistribution(
        holders=holders,
        total_supply=TokenHelper.get_total_supply(),
        holder_count=len(holders),
    )


# ============================================================================
# ICRC-3 Indexer Types and Methods (for transaction history)
# ============================================================================


class Spender(Record):
    owner: Principal
    subaccount: Opt[blob]


class IndexerTransfer(Record):
    to: Account
    fee: Opt[nat]
    from_: Account
    memo: Opt[Vec[nat8]]
    created_at_time: Opt[nat]
    amount: nat
    spender: Opt[Spender]


class IndexerMint(Record):
    to: Account
    memo: Opt[Vec[nat8]]
    created_at_time: Opt[nat]
    amount: nat


class IndexerBurn(Record):
    from_: Account
    memo: Opt[Vec[nat8]]
    created_at_time: Opt[nat]
    amount: nat
    spender: Opt[Spender]


class IndexerTransaction(Record):
    burn: Opt[IndexerBurn]
    kind: text
    mint: Opt[IndexerMint]
    approve: Opt[nat]  # Simplified - not implementing approvals
    timestamp: nat
    transfer: Opt[IndexerTransfer]


class AccountTransaction(Record):
    id: nat
    transaction: IndexerTransaction


class GetAccountTransactionsRequest(Record):
    account: Account
    start: Opt[nat]
    max_results: nat


class GetAccountTransactionsResponse(Record):
    balance: nat
    transactions: Vec[AccountTransaction]
    oldest_tx_id: Opt[nat]


class GetTransactionsResult(Variant, total=False):
    Ok: GetAccountTransactionsResponse
    Err: text


@query
def get_account_transactions(
    request: GetAccountTransactionsRequest,
) -> GetTransactionsResult:
    """
    ICRC-3 compatible method to get transaction history for an account.
    This is the indexer interface that the vault extension expects.
    """
    owner_str = request["account"]["owner"].to_str()
    subaccount = request["account"].get("subaccount")
    start = request.get("start")
    max_results = request.get("max_results") if request.get("max_results") else 20

    logger.info(
        f"get_account_transactions: owner={owner_str}, start={start}, max_results={max_results}"
    )

    # Get transactions for this account
    txs = TransactionHelper.get_transactions_for_account(
        owner=owner_str,
        subaccount=subaccount,
        start=start,
        max_results=max_results,
    )

    # Convert to AccountTransaction format
    account_transactions = []
    oldest_tx_id = None

    for tx in txs:
        # Track oldest transaction ID
        if oldest_tx_id is None or tx.id < oldest_tx_id:
            oldest_tx_id = tx.id

        # Build the transaction record based on kind
        # (forced_transfer is surfaced like a regular transfer)
        if tx.kind in ("transfer", "forced_transfer"):
            from_subaccount = (
                bytes.fromhex(tx.from_subaccount) if tx.from_subaccount else None
            )
            to_subaccount = (
                bytes.fromhex(tx.to_subaccount) if tx.to_subaccount else None
            )

            transfer_record = IndexerTransfer(
                to=Account(
                    owner=Principal.from_str(tx.to_owner), subaccount=to_subaccount
                ),
                fee=tx.fee if tx.fee else None,
                from_=Account(
                    owner=Principal.from_str(tx.from_owner), subaccount=from_subaccount
                ),
                memo=None,
                created_at_time=tx.timestamp,
                amount=tx.amount,
                spender=None,
            )

            indexer_tx = IndexerTransaction(
                burn=None,
                kind="transfer",
                mint=None,
                approve=None,
                timestamp=tx.timestamp,
                transfer=transfer_record,
            )
        elif tx.kind == "mint":
            to_subaccount = (
                bytes.fromhex(tx.to_subaccount) if tx.to_subaccount else None
            )

            mint_record = IndexerMint(
                to=Account(
                    owner=Principal.from_str(tx.to_owner), subaccount=to_subaccount
                ),
                memo=None,
                created_at_time=tx.timestamp,
                amount=tx.amount,
            )

            indexer_tx = IndexerTransaction(
                burn=None,
                kind="mint",
                mint=mint_record,
                approve=None,
                timestamp=tx.timestamp,
                transfer=None,
            )
        else:
            # Unknown transaction type, skip
            continue

        account_transactions.append(
            AccountTransaction(
                id=tx.id,
                transaction=indexer_tx,
            )
        )

    # Get current balance
    balance = TokenHelper.get_balance(owner_str, subaccount)

    response = GetAccountTransactionsResponse(
        balance=balance,
        transactions=account_transactions,
        oldest_tx_id=oldest_tx_id,
    )

    logger.info(
        f"Returning {len(account_transactions)} transactions, balance={balance}"
    )

    return GetTransactionsResult(Ok=response)


# ============================================================================
# Transaction Explorer Types and Methods
# ============================================================================


class TransactionInfo(Record):
    id: nat
    kind: text
    timestamp: nat
    from_address: text
    to_address: text
    amount: nat
    fee: nat


class TransactionListResponse(Record):
    transactions: Vec[TransactionInfo]
    total_count: nat
    page: nat
    page_size: nat
    has_more: bool


class TransactionDetailResponse(Record):
    id: nat
    kind: text
    timestamp: nat
    from_owner: text
    from_subaccount: text
    to_owner: text
    to_subaccount: text
    amount: nat
    fee: nat
    memo: text


@query
def get_transactions(page: nat, page_size: nat) -> TransactionListResponse:
    """Get paginated list of all transactions."""
    if page_size == 0:
        page_size = 20
    if page_size > 100:
        page_size = 100

    all_txs = list(TransactionLog.instances())
    all_txs.sort(key=lambda x: x.id, reverse=True)

    total_count = len(all_txs)
    start_idx = page * page_size
    end_idx = start_idx + page_size

    page_txs = all_txs[start_idx:end_idx]

    transactions = []
    for tx in page_txs:
        from_addr = tx.from_owner
        if tx.from_subaccount:
            from_addr = f"{from_addr}:{tx.from_subaccount[:8]}"

        to_addr = tx.to_owner
        if tx.to_subaccount:
            to_addr = f"{to_addr}:{tx.to_subaccount[:8]}"

        transactions.append(
            TransactionInfo(
                id=tx.id,
                kind=tx.kind,
                timestamp=tx.timestamp,
                from_address=from_addr,
                to_address=to_addr,
                amount=tx.amount,
                fee=tx.fee or 0,
            )
        )

    return TransactionListResponse(
        transactions=transactions,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_more=end_idx < total_count,
    )


@query
def get_transaction(tx_id: nat) -> Opt[TransactionDetailResponse]:
    """Get details of a specific transaction by ID."""
    tx = TransactionLog[tx_id]
    if tx is None:
        return None

    return TransactionDetailResponse(
        id=tx.id,
        kind=tx.kind,
        timestamp=tx.timestamp,
        from_owner=tx.from_owner,
        from_subaccount=tx.from_subaccount,
        to_owner=tx.to_owner,
        to_subaccount=tx.to_subaccount,
        amount=tx.amount,
        fee=tx.fee or 0,
        memo=tx.memo or "",
    )


@query
def get_top_holders(limit: nat) -> Vec[HolderInfo]:
    """Get the top N token holders by balance."""
    if limit == 0:
        limit = 10
    if limit > 100:
        limit = 100

    holders = []
    for balance in TokenBalance.instances():
        if balance.amount and balance.amount > 0:
            holders.append(HolderInfo(address=balance.id, balance=balance.amount))

    holders.sort(key=lambda h: h["balance"], reverse=True)
    return holders[:limit]
