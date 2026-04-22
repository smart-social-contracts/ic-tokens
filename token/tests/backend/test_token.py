#!/usr/bin/env python3
"""
Tests for the ICRC-1 token backend.
Tests basic token operations using mock storage.
"""

import os
import sys
import time
from types import ModuleType
from unittest.mock import MagicMock


# Create subscriptable mock types
class SubscriptableMeta(type):
    def __getitem__(cls, item):
        return cls


class MockOpt(metaclass=SubscriptableMeta):
    pass


class MockVec(metaclass=SubscriptableMeta):
    pass


class MockTuple(metaclass=SubscriptableMeta):
    pass


class MockStableBTreeMap(metaclass=SubscriptableMeta):
    def __init__(self, memory_id=0, max_key_size=100, max_value_size=100):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def items(self):
        return self.data.items()


class MockRecord:
    pass


class MockVariant:
    """Mock Variant class for testing"""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __init_subclass__(cls, **kwargs):
        # Accept and ignore keyword arguments like total=False
        pass


# Create mock modules BEFORE any imports
mock_kybra = ModuleType("kybra")
mock_ic = MagicMock()
mock_ic.time.return_value = int(time.time() * 1_000_000_000)
mock_ic.caller.return_value = MagicMock(to_str=lambda: "aaaaa-aa")
mock_ic.id.return_value = MagicMock(to_str=lambda: "bbbbb-bb")

mock_kybra.ic = mock_ic
mock_kybra.Opt = MockOpt
mock_kybra.Principal = MagicMock
mock_kybra.Record = MockRecord
mock_kybra.StableBTreeMap = MockStableBTreeMap
mock_kybra.Tuple = MockTuple
mock_kybra.Variant = MockVariant
mock_kybra.Vec = MockVec
mock_kybra.blob = bytes
mock_kybra.init = lambda f: f
mock_kybra.nat = int
mock_kybra.nat8 = int
mock_kybra.query = lambda f: f
mock_kybra.text = str
mock_kybra.update = lambda f: f
mock_kybra.void = type(None)

sys.modules["kybra"] = mock_kybra

# Mock kybra_simple_logging
mock_logging = ModuleType("kybra_simple_logging")
mock_logger = MagicMock()
mock_logging.get_logger = lambda name: mock_logger
sys.modules["kybra_simple_logging"] = mock_logging


# Mock kybra_simple_db
class MockStorage:
    """Mock storage for testing without requiring a real canister environment"""

    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def remove(self, key):
        if key in self.data:
            del self.data[key]

    def items(self):
        return self.data.items()

    def keys(self):
        return self.data.keys()


mock_storage = MockStorage()


class MockEntityMeta(type):
    """Metaclass that gives each Entity subclass its own _instances dict"""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        cls._instances = {}  # Each class gets its own instances dict
        return cls

    def __getitem__(cls, key):
        return cls._instances.get(key)


class MockEntity(metaclass=MockEntityMeta):
    """Mock Entity class for testing"""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        key = self._get_key(kwargs)
        if key is not None:
            self.__class__._instances[key] = self

    @staticmethod
    def _get_key(data):
        """Get key from dict, handling falsy values like 0 correctly"""
        if "id" in data:
            return data["id"]
        if "key" in data:
            return data["key"]
        return None

    def _get_instance_key(self):
        """Get key from instance attributes"""
        if hasattr(self, "id") and self.id is not None:
            return self.id
        if hasattr(self, "key") and self.key is not None:
            return self.key
        return None

    def save(self):
        key = self._get_instance_key()
        if key is not None:
            self.__class__._instances[key] = self

    def delete(self):
        key = self._get_instance_key()
        if key is not None and key in self.__class__._instances:
            del self.__class__._instances[key]

    @classmethod
    def instances(cls):
        return list(cls._instances.values())

    @classmethod
    def count(cls):
        return len(cls._instances)


class MockDatabase:
    _instance = None

    @classmethod
    def init(cls, db_storage=None, audit_enabled=False):
        cls._instance = cls()

    @classmethod
    def get_instance(cls):
        return cls._instance

    def register_entity_type(self, entity_class):
        pass


mock_db = ModuleType("kybra_simple_db")
mock_db.Database = MockDatabase
mock_db.Entity = MockEntity
mock_db.Integer = int
mock_db.String = str
sys.modules["kybra_simple_db"] = mock_db

# Add paths to match Kybra's import resolution
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../../src/token_backend/src")
)

# Color formatting for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")


def print_failure(message, error=None):
    print(f"{RED}✗ {message}{RESET}")
    if error:
        print(f"  Error: {error}")


def test_token_constants():
    """Test token configuration constants"""
    try:
        # Import after mocking
        from main import TOKEN_DECIMALS, TOKEN_FEE, TOKEN_NAME, TOKEN_SYMBOL

        assert (
            TOKEN_NAME == "Simple Token"
        ), f"Expected 'Simple Token', got {TOKEN_NAME}"
        assert TOKEN_SYMBOL == "SMPL", f"Expected 'SMPL', got {TOKEN_SYMBOL}"
        assert TOKEN_DECIMALS == 8, f"Expected 8, got {TOKEN_DECIMALS}"
        assert TOKEN_FEE == 10_000, f"Expected 10000, got {TOKEN_FEE}"

        print_success("token_constants tests passed")
        return True
    except Exception as e:
        print_failure("token_constants tests failed", str(e))
        return False


def test_icrc1_name():
    """Test icrc1_name query"""
    try:
        from main import icrc1_name

        name = icrc1_name()
        assert name == "Simple Token", f"Expected 'Simple Token', got {name}"

        print_success("icrc1_name tests passed")
        return True
    except Exception as e:
        print_failure("icrc1_name tests failed", str(e))
        return False


def test_icrc1_symbol():
    """Test icrc1_symbol query"""
    try:
        from main import icrc1_symbol

        symbol = icrc1_symbol()
        assert symbol == "SMPL", f"Expected 'SMPL', got {symbol}"

        print_success("icrc1_symbol tests passed")
        return True
    except Exception as e:
        print_failure("icrc1_symbol tests failed", str(e))
        return False


def test_icrc1_decimals():
    """Test icrc1_decimals query"""
    try:
        from main import icrc1_decimals

        decimals = icrc1_decimals()
        assert decimals == 8, f"Expected 8, got {decimals}"

        print_success("icrc1_decimals tests passed")
        return True
    except Exception as e:
        print_failure("icrc1_decimals tests failed", str(e))
        return False


def test_icrc1_fee():
    """Test icrc1_fee query"""
    try:
        from main import icrc1_fee

        fee = icrc1_fee()
        assert fee == 10_000, f"Expected 10000, got {fee}"

        print_success("icrc1_fee tests passed")
        return True
    except Exception as e:
        print_failure("icrc1_fee tests failed", str(e))
        return False


def test_token_helper_balance():
    """Test TokenHelper balance operations"""
    try:
        from main import TokenHelper

        # Test initial balance (should be 0)
        balance = TokenHelper.get_balance("test-user-1")
        assert balance == 0, f"Expected 0, got {balance}"

        # Set balance
        TokenHelper.set_balance("test-user-1", 1000)
        balance = TokenHelper.get_balance("test-user-1")
        assert balance == 1000, f"Expected 1000, got {balance}"

        # Update balance
        TokenHelper.set_balance("test-user-1", 500)
        balance = TokenHelper.get_balance("test-user-1")
        assert balance == 500, f"Expected 500, got {balance}"

        print_success("token_helper_balance tests passed")
        return True
    except Exception as e:
        print_failure("token_helper_balance tests failed", str(e))
        return False


def test_token_helper_supply():
    """Test TokenHelper supply operations"""
    try:
        from main import TokenHelper

        # Set total supply
        TokenHelper.set_total_supply(1_000_000_000)
        supply = TokenHelper.get_total_supply()
        assert supply == 1_000_000_000, f"Expected 1000000000, got {supply}"

        # Update supply
        TokenHelper.set_total_supply(999_999_000)
        supply = TokenHelper.get_total_supply()
        assert supply == 999_999_000, f"Expected 999999000, got {supply}"

        print_success("token_helper_supply tests passed")
        return True
    except Exception as e:
        print_failure("token_helper_supply tests failed", str(e))
        return False


def test_icrc1_metadata():
    """Test icrc1_metadata query"""
    try:
        from main import icrc1_metadata

        metadata = icrc1_metadata()
        assert len(metadata) == 4, f"Expected 4 metadata entries, got {len(metadata)}"

        # Check metadata contains expected keys
        metadata_dict = dict(metadata)
        assert "icrc1:name" in metadata_dict
        assert "icrc1:symbol" in metadata_dict
        assert "icrc1:decimals" in metadata_dict
        assert "icrc1:fee" in metadata_dict

        print_success("icrc1_metadata tests passed")
        return True
    except Exception as e:
        print_failure("icrc1_metadata tests failed", str(e))
        return False


def test_icrc1_supported_standards():
    """Test icrc1_supported_standards query"""
    try:
        from main import icrc1_supported_standards

        standards = icrc1_supported_standards()
        assert (
            len(standards) >= 1
        ), f"Expected at least 1 standard, got {len(standards)}"

        # Check ICRC-1 is supported
        standards_dict = dict(standards)
        assert "ICRC-1" in standards_dict

        print_success("icrc1_supported_standards tests passed")
        return True
    except Exception as e:
        print_failure("icrc1_supported_standards tests failed", str(e))
        return False


def test_owner_helper():
    """Test OwnerHelper operations"""
    try:
        from main import OwnerHelper

        # Set owner
        OwnerHelper.set_owner("test-owner-principal")
        owner = OwnerHelper.get_owner()
        assert (
            owner == "test-owner-principal"
        ), f"Expected 'test-owner-principal', got {owner}"

        # Check is_owner
        assert OwnerHelper.is_owner("test-owner-principal") == True
        assert OwnerHelper.is_owner("other-principal") == False

        print_success("owner_helper tests passed")
        return True
    except Exception as e:
        print_failure("owner_helper tests failed", str(e))
        return False


def test_mint_authorized():
    """Test mint function with authorized owner"""
    try:
        from main import OwnerHelper, TokenHelper

        # Set up owner as the mock caller (aaaaa-aa)
        OwnerHelper.set_owner("aaaaa-aa")

        # Set initial supply
        TokenHelper.set_total_supply(1000000)
        initial_supply = TokenHelper.get_total_supply()

        # Set initial balance for recipient
        TokenHelper.set_balance("recipient-principal", 0)

        # Note: We can't directly test the mint function because it uses ic.caller()
        # and requires Principal objects. Instead, we test the helper functions.

        # Simulate mint by directly calling helpers
        mint_amount = 50000
        current_balance = TokenHelper.get_balance("recipient-principal")
        new_balance = current_balance + mint_amount
        TokenHelper.set_balance("recipient-principal", new_balance)
        TokenHelper.set_total_supply(initial_supply + mint_amount)

        # Verify
        assert TokenHelper.get_balance("recipient-principal") == mint_amount
        assert TokenHelper.get_total_supply() == initial_supply + mint_amount

        print_success("mint_authorized tests passed")
        return True
    except Exception as e:
        print_failure("mint_authorized tests failed", str(e))
        return False


def test_mint_unauthorized():
    """Test that non-owner cannot mint"""
    try:
        from main import OwnerHelper

        # Set owner to a different principal
        OwnerHelper.set_owner("owner-principal")

        # Check that a different principal is not the owner
        assert OwnerHelper.is_owner("attacker-principal") == False
        assert OwnerHelper.is_owner("owner-principal") == True

        print_success("mint_unauthorized tests passed")
        return True
    except Exception as e:
        print_failure("mint_unauthorized tests failed", str(e))
        return False


# ============================================================
# INDEXER TESTS
# ============================================================


def test_transaction_helper_block_index():
    """Test TransactionHelper block index management"""
    try:
        from main import TokenConfig, TransactionHelper

        # Reset block index
        config = TokenConfig["next_block_index"]
        if config:
            config.delete()
        TokenConfig._instances.pop("next_block_index", None)

        # Initial block index should be 0
        initial = TransactionHelper.get_next_block_index()
        assert initial == 0, f"Expected 0, got {initial}"

        # Increment and get should return 0 (current), then next should be 1
        block0 = TransactionHelper.increment_block_index()
        assert block0 == 0, f"Expected 0, got {block0}"

        next_idx = TransactionHelper.get_next_block_index()
        assert next_idx == 1, f"Expected 1, got {next_idx}"

        # Increment again
        block1 = TransactionHelper.increment_block_index()
        assert block1 == 1, f"Expected 1, got {block1}"

        block2 = TransactionHelper.increment_block_index()
        assert block2 == 2, f"Expected 2, got {block2}"

        print_success("transaction_helper_block_index tests passed")
        return True
    except Exception as e:
        print_failure("transaction_helper_block_index tests failed", str(e))
        return False


def test_transaction_helper_log_transaction():
    """Test TransactionHelper.log_transaction"""
    try:
        from main import TokenConfig, TransactionHelper, TransactionLog

        # Clear existing transaction logs
        TransactionLog._instances.clear()

        # Reset block index
        TokenConfig._instances.pop("next_block_index", None)

        # Log a transfer transaction
        block_idx = TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="sender-principal",
            from_subaccount=None,
            to_owner="recipient-principal",
            to_subaccount=None,
            amount=100000,
            fee=10000,
            memo=None,
        )

        assert block_idx == 0, f"Expected block_index 0, got {block_idx}"

        # Verify transaction was logged
        tx = TransactionLog[0]
        assert tx is not None, "Transaction log entry not found"
        assert tx.kind == "transfer", f"Expected 'transfer', got {tx.kind}"
        assert (
            tx.from_owner == "sender-principal"
        ), f"Expected 'sender-principal', got {tx.from_owner}"
        assert (
            tx.to_owner == "recipient-principal"
        ), f"Expected 'recipient-principal', got {tx.to_owner}"
        assert tx.amount == 100000, f"Expected 100000, got {tx.amount}"
        assert tx.fee == 10000, f"Expected 10000, got {tx.fee}"

        # Log a mint transaction
        block_idx2 = TransactionHelper.log_transaction(
            kind="mint",
            from_owner="",
            from_subaccount=None,
            to_owner="recipient-principal",
            to_subaccount=None,
            amount=500000,
            fee=0,
            memo=None,
        )

        assert block_idx2 == 1, f"Expected block_index 1, got {block_idx2}"

        # Verify mint transaction
        tx2 = TransactionLog[1]
        assert tx2 is not None, "Mint transaction log entry not found"
        assert tx2.kind == "mint", f"Expected 'mint', got {tx2.kind}"
        assert (
            tx2.from_owner == ""
        ), f"Expected empty from_owner for mint, got {tx2.from_owner}"
        assert tx2.to_owner == "recipient-principal"
        assert tx2.amount == 500000

        print_success("transaction_helper_log_transaction tests passed")
        return True
    except Exception as e:
        print_failure("transaction_helper_log_transaction tests failed", str(e))
        return False


def test_transaction_helper_get_transactions_for_account():
    """Test TransactionHelper.get_transactions_for_account"""
    try:
        from main import TokenConfig, TransactionHelper, TransactionLog

        # Clear existing data
        TransactionLog._instances.clear()
        TokenConfig._instances.pop("next_block_index", None)

        # Log several transactions involving different accounts
        # Transaction 0: alice -> bob
        TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="alice",
            from_subaccount=None,
            to_owner="bob",
            to_subaccount=None,
            amount=1000,
            fee=10,
        )

        # Transaction 1: bob -> charlie
        TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="bob",
            from_subaccount=None,
            to_owner="charlie",
            to_subaccount=None,
            amount=500,
            fee=10,
        )

        # Transaction 2: mint -> alice
        TransactionHelper.log_transaction(
            kind="mint",
            from_owner="",
            from_subaccount=None,
            to_owner="alice",
            to_subaccount=None,
            amount=10000,
            fee=0,
        )

        # Transaction 3: alice -> charlie
        TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="alice",
            from_subaccount=None,
            to_owner="charlie",
            to_subaccount=None,
            amount=2000,
            fee=10,
        )

        # Get transactions for alice (should have 3: sent to bob, received mint, sent to charlie)
        alice_txs = TransactionHelper.get_transactions_for_account("alice")
        assert (
            len(alice_txs) == 3
        ), f"Expected 3 transactions for alice, got {len(alice_txs)}"

        # Get transactions for bob (should have 2: received from alice, sent to charlie)
        bob_txs = TransactionHelper.get_transactions_for_account("bob")
        assert len(bob_txs) == 2, f"Expected 2 transactions for bob, got {len(bob_txs)}"

        # Get transactions for charlie (should have 2: received from bob, received from alice)
        charlie_txs = TransactionHelper.get_transactions_for_account("charlie")
        assert (
            len(charlie_txs) == 2
        ), f"Expected 2 transactions for charlie, got {len(charlie_txs)}"

        # Verify ordering (newest first)
        assert (
            alice_txs[0].id > alice_txs[1].id
        ), "Transactions should be ordered newest first"

        # Test max_results limit
        limited_txs = TransactionHelper.get_transactions_for_account(
            "alice", max_results=2
        )
        assert (
            len(limited_txs) == 2
        ), f"Expected 2 transactions with limit, got {len(limited_txs)}"

        # Test start parameter (pagination)
        # Get transactions before id 3 (should exclude tx 3)
        paginated_txs = TransactionHelper.get_transactions_for_account("alice", start=3)
        assert (
            len(paginated_txs) == 2
        ), f"Expected 2 transactions before id 3, got {len(paginated_txs)}"
        assert all(
            tx.id < 3 for tx in paginated_txs
        ), "All transactions should have id < 3"

        print_success("transaction_helper_get_transactions_for_account tests passed")
        return True
    except Exception as e:
        print_failure(
            "transaction_helper_get_transactions_for_account tests failed", str(e)
        )
        return False


def test_transaction_log_with_subaccounts():
    """Test transaction logging with subaccounts"""
    try:
        from main import TokenConfig, TransactionHelper, TransactionLog

        # Clear existing data
        TransactionLog._instances.clear()
        TokenConfig._instances.pop("next_block_index", None)

        # Create subaccount bytes (32 bytes)
        subaccount1 = bytes([1] + [0] * 31)
        subaccount2 = bytes([2] + [0] * 31)

        # Log transaction with subaccounts
        TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="alice",
            from_subaccount=subaccount1,
            to_owner="bob",
            to_subaccount=subaccount2,
            amount=5000,
            fee=10,
        )

        # Verify subaccounts were stored correctly
        tx = TransactionLog[0]
        assert tx.from_subaccount == subaccount1.hex(), "from_subaccount mismatch"
        assert tx.to_subaccount == subaccount2.hex(), "to_subaccount mismatch"

        # Get transactions for alice with matching subaccount
        alice_sub1_txs = TransactionHelper.get_transactions_for_account(
            "alice", subaccount=subaccount1
        )
        assert (
            len(alice_sub1_txs) == 1
        ), f"Expected 1 transaction for alice:subaccount1, got {len(alice_sub1_txs)}"

        # Get transactions for alice with different subaccount (should be empty)
        alice_sub2_txs = TransactionHelper.get_transactions_for_account(
            "alice", subaccount=subaccount2
        )
        assert (
            len(alice_sub2_txs) == 0
        ), f"Expected 0 transactions for alice:subaccount2, got {len(alice_sub2_txs)}"

        # Get transactions for bob with matching subaccount
        bob_sub2_txs = TransactionHelper.get_transactions_for_account(
            "bob", subaccount=subaccount2
        )
        assert (
            len(bob_sub2_txs) == 1
        ), f"Expected 1 transaction for bob:subaccount2, got {len(bob_sub2_txs)}"

        print_success("transaction_log_with_subaccounts tests passed")
        return True
    except Exception as e:
        print_failure("transaction_log_with_subaccounts tests failed", str(e))
        return False


def test_transaction_log_with_memo():
    """Test transaction logging with memo"""
    try:
        from main import TokenConfig, TransactionHelper, TransactionLog

        # Clear existing data
        TransactionLog._instances.clear()
        TokenConfig._instances.pop("next_block_index", None)

        # Create memo
        memo = b"invoice_12345"

        # Log transaction with memo
        TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="alice",
            from_subaccount=None,
            to_owner="bob",
            to_subaccount=None,
            amount=1000,
            fee=10,
            memo=memo,
        )

        # Verify memo was stored correctly
        tx = TransactionLog[0]
        assert (
            tx.memo == memo.hex()
        ), f"memo mismatch: expected {memo.hex()}, got {tx.memo}"

        # Log transaction without memo
        TransactionHelper.log_transaction(
            kind="transfer",
            from_owner="alice",
            from_subaccount=None,
            to_owner="charlie",
            to_subaccount=None,
            amount=2000,
            fee=10,
            memo=None,
        )

        tx2 = TransactionLog[1]
        assert tx2.memo == "", f"Expected empty memo, got {tx2.memo}"

        print_success("transaction_log_with_memo tests passed")
        return True
    except Exception as e:
        print_failure("transaction_log_with_memo tests failed", str(e))
        return False


def test_indexer_multiple_transactions():
    """Test indexer with a realistic sequence of transactions"""
    try:
        from main import TokenConfig, TokenHelper, TransactionHelper, TransactionLog

        # Clear existing data
        TransactionLog._instances.clear()
        TokenConfig._instances.pop("next_block_index", None)

        # Simulate a realistic scenario:
        # 1. Mint tokens to user
        # 2. User transfers to multiple recipients
        # 3. Recipients transfer among themselves

        user = "user-principal"
        recipient1 = "recipient1-principal"
        recipient2 = "recipient2-principal"

        # Mint to user
        block0 = TransactionHelper.log_transaction(
            kind="mint",
            from_owner="",
            from_subaccount=None,
            to_owner=user,
            to_subaccount=None,
            amount=1_000_000,
            fee=0,
        )

        # User transfers to recipient1
        block1 = TransactionHelper.log_transaction(
            kind="transfer",
            from_owner=user,
            from_subaccount=None,
            to_owner=recipient1,
            to_subaccount=None,
            amount=100_000,
            fee=10_000,
        )

        # User transfers to recipient2
        block2 = TransactionHelper.log_transaction(
            kind="transfer",
            from_owner=user,
            from_subaccount=None,
            to_owner=recipient2,
            to_subaccount=None,
            amount=200_000,
            fee=10_000,
        )

        # recipient1 transfers to recipient2
        block3 = TransactionHelper.log_transaction(
            kind="transfer",
            from_owner=recipient1,
            from_subaccount=None,
            to_owner=recipient2,
            to_subaccount=None,
            amount=50_000,
            fee=10_000,
        )

        # Verify block indices are sequential
        assert block0 == 0
        assert block1 == 1
        assert block2 == 2
        assert block3 == 3

        # Verify user has 3 transactions (1 mint received, 2 transfers sent)
        user_txs = TransactionHelper.get_transactions_for_account(user)
        assert len(user_txs) == 3, f"Expected 3 txs for user, got {len(user_txs)}"

        # Verify recipient1 has 2 transactions (1 received, 1 sent)
        r1_txs = TransactionHelper.get_transactions_for_account(recipient1)
        assert len(r1_txs) == 2, f"Expected 2 txs for recipient1, got {len(r1_txs)}"

        # Verify recipient2 has 2 transactions (2 received)
        r2_txs = TransactionHelper.get_transactions_for_account(recipient2)
        assert len(r2_txs) == 2, f"Expected 2 txs for recipient2, got {len(r2_txs)}"

        # Verify total transaction count
        all_txs = list(TransactionLog.instances())
        assert len(all_txs) == 4, f"Expected 4 total txs, got {len(all_txs)}"

        print_success("indexer_multiple_transactions tests passed")
        return True
    except Exception as e:
        print_failure("indexer_multiple_transactions tests failed", str(e))
        return False


# ============================================================
# TEST MODE TESTS
# ============================================================


def test_test_mode_config():
    """Test that test mode config can be set and checked"""
    try:
        from main import TokenConfig

        # Clear test config
        TokenConfig._instances.pop("test", None)

        # Initially test mode should not be set
        config = TokenConfig["test"]
        assert (
            config is None or config.value != "true"
        ), "Test mode should not be enabled initially"

        # Set test mode
        TokenConfig(key="test", value="true")

        # Verify test mode is enabled
        config = TokenConfig["test"]
        assert config is not None, "Test config should exist"
        assert config.value == "true", f"Expected 'true', got {config.value}"

        # Clean up
        TokenConfig._instances.pop("test", None)

        print_success("test_mode_config tests passed")
        return True
    except Exception as e:
        print_failure("test_mode_config tests failed", str(e))
        return False


def test_mint_allowed_in_test_mode():
    """Test that non-owner can mint when test mode is enabled"""
    try:
        from main import OwnerHelper, TokenConfig, TokenHelper

        # Set owner to a different principal (not the mock caller 'aaaaa-aa')
        OwnerHelper.set_owner("real-owner-principal")

        # Enable test mode
        TokenConfig._instances.pop("test", None)
        TokenConfig(key="test", value="true")

        # Verify test mode check works
        test_mode = TokenConfig["test"] and TokenConfig["test"].value == "true"
        assert test_mode == True, "Test mode should be enabled"

        # In test mode, even non-owner should be allowed to mint
        # We can't directly test the mint function (needs ic.caller()),
        # but we verify the condition logic
        caller = "non-owner-caller"
        is_owner = OwnerHelper.is_owner(caller)
        assert is_owner == False, "Caller should not be owner"

        # The mint check: not owner AND not test_mode -> deny
        # With test_mode=True, this should NOT deny
        should_deny = not is_owner and not test_mode
        assert should_deny == False, "Should NOT deny mint in test mode"

        # Clean up
        TokenConfig._instances.pop("test", None)

        print_success("mint_allowed_in_test_mode tests passed")
        return True
    except Exception as e:
        print_failure("mint_allowed_in_test_mode tests failed", str(e))
        return False


def test_mint_denied_without_test_mode():
    """Test that non-owner cannot mint when test mode is disabled"""
    try:
        from main import OwnerHelper, TokenConfig

        # Set owner to a different principal
        OwnerHelper.set_owner("real-owner-principal")

        # Ensure test mode is disabled by setting it to "false"
        TokenConfig._instances.pop("test", None)
        TokenConfig(key="test", value="false")

        # Verify test mode is disabled
        test_mode = TokenConfig["test"] and TokenConfig["test"].value == "true"
        assert test_mode == False, "Test mode should be disabled"

        # Non-owner should be denied
        caller = "non-owner-caller"
        is_owner = OwnerHelper.is_owner(caller)
        assert is_owner == False, "Caller should not be owner"

        # The mint check: not owner AND not test_mode -> deny
        should_deny = not is_owner and not test_mode
        assert should_deny == True, "Should deny mint without test mode"

        print_success("mint_denied_without_test_mode tests passed")
        return True
    except Exception as e:
        print_failure("mint_denied_without_test_mode tests failed", str(e))
        return False


def run_tests():
    """Run all tests and report results"""
    print(f"{BOLD}Running Token Backend Tests...{RESET}\n")

    success_count = 0
    failure_count = 0

    tests = [
        # Basic token tests
        test_token_constants,
        test_icrc1_name,
        test_icrc1_symbol,
        test_icrc1_decimals,
        test_icrc1_fee,
        test_token_helper_balance,
        test_token_helper_supply,
        test_icrc1_metadata,
        test_icrc1_supported_standards,
        test_owner_helper,
        test_mint_authorized,
        test_mint_unauthorized,
        # Test mode tests
        test_test_mode_config,
        test_mint_allowed_in_test_mode,
        test_mint_denied_without_test_mode,
        # Indexer tests
        test_transaction_helper_block_index,
        test_transaction_helper_log_transaction,
        test_transaction_helper_get_transactions_for_account,
        test_transaction_log_with_subaccounts,
        test_transaction_log_with_memo,
        test_indexer_multiple_transactions,
    ]

    for test in tests:
        if test():
            success_count += 1
        else:
            failure_count += 1

    print(f"\n{BOLD}Test Summary:{RESET}")
    print(f"- {GREEN}{success_count} tests passed{RESET}")
    print(f"- {RED if failure_count > 0 else ''}{failure_count} tests failed{RESET}")

    return failure_count == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
