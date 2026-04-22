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


class TokenMetadataRecord(Record):
    name: text
    symbol: text
    decimals: nat8
    fee: nat
    total_supply: nat


class InitArgs(Record):
    name: text
    symbol: text
    decimals: nat8
    total_supply: nat
    fee: nat
    test: Opt[bool]


class HolderInfo(Record):
    address: text
    balance: nat


class TokenDistribution(Record):
    holders: Vec["HolderInfo"]
    total_supply: nat
    holder_count: nat


# Token configuration
TOKEN_NAME = "Simple Token"
TOKEN_SYMBOL = "SMPL"
TOKEN_DECIMALS: nat8 = 8
TOKEN_FEE: nat = 10_000


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
    deployer = ic.caller().to_str()
    OwnerHelper.set_owner(deployer)
    TokenHelper.set_balance(deployer, args["total_supply"])
    TokenHelper.set_total_supply(args["total_supply"])
    if args.get("test"):
        TokenConfig(key="test", value="true")
        logger.info("Test mode enabled - public minting allowed")
    logger.info(f"Token initialized. Supply: {args['total_supply']} to {deployer}")


@query
def icrc1_name() -> text:
    return TOKEN_NAME


@query
def icrc1_symbol() -> text:
    return TOKEN_SYMBOL


@query
def icrc1_decimals() -> nat8:
    return TOKEN_DECIMALS


@query
def icrc1_fee() -> nat:
    return TOKEN_FEE


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
        ("icrc1:name", TOKEN_NAME),
        ("icrc1:symbol", TOKEN_SYMBOL),
        ("icrc1:decimals", str(TOKEN_DECIMALS)),
        ("icrc1:fee", str(TOKEN_FEE)),
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

    sender_balance = TokenHelper.get_balance(caller, args.get("from_subaccount"))
    fee = args.get("fee") if args.get("fee") is not None else TOKEN_FEE
    total_deduction = args["amount"] + fee

    if sender_balance < total_deduction:
        logger.warning(f"Insufficient balance: {sender_balance} < {total_deduction}")
        return TransferResult(
            success=False,
            block_index=None,
            error=f"Insufficient balance. Have {sender_balance}, need {total_deduction}",
        )

    recipient = args["to"]["owner"].to_str()
    recipient_balance = TokenHelper.get_balance(recipient, args["to"].get("subaccount"))

    TokenHelper.set_balance(
        caller, sender_balance - total_deduction, args.get("from_subaccount")
    )
    TokenHelper.set_balance(
        recipient, recipient_balance + args["amount"], args["to"].get("subaccount")
    )

    current_supply = TokenHelper.get_total_supply()
    TokenHelper.set_total_supply(current_supply - fee)

    # Log the transaction for indexer
    block_index = TransactionHelper.log_transaction(
        kind="transfer",
        from_owner=caller,
        from_subaccount=args.get("from_subaccount"),
        to_owner=recipient,
        to_subaccount=args["to"].get("subaccount"),
        amount=args["amount"],
        fee=fee,
        memo=args.get("memo"),
    )

    logger.info(
        f"Transfer successful: {args['amount']} tokens transferred, block_index={block_index}"
    )

    return TransferResult(success=True, block_index=block_index, error=None)


@update
def mint(args: MintArgs) -> MintResult:
    caller = ic.caller().to_str()
    logger.info(
        f"Mint request from {caller}: {args['amount']} to {args['to']['owner'].to_str()}"
    )

    test_mode = TokenConfig["test"] and TokenConfig["test"].value == "true"
    if not OwnerHelper.is_owner(caller) and not test_mode:
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


@query
def get_owner() -> text:
    owner = OwnerHelper.get_owner()
    return owner if owner else ""


@query
def get_token_info() -> TokenMetadataRecord:
    return TokenMetadataRecord(
        name=TOKEN_NAME,
        symbol=TOKEN_SYMBOL,
        decimals=TOKEN_DECIMALS,
        fee=TOKEN_FEE,
        total_supply=TokenHelper.get_total_supply(),
    )


@query
def get_my_balance() -> nat:
    return TokenHelper.get_balance(ic.caller().to_str())


@query
def get_my_principal() -> text:
    return ic.caller().to_str()


@query
def is_test_mode() -> bool:
    config = TokenConfig["test"]
    return config is not None and config.value == "true"


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
        if tx.kind == "transfer":
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
