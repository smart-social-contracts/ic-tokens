#!/usr/bin/env python3
"""
Integration tests for ICRC-1 token backend.
Uses dfx canister calls with --output json to test the deployed canister.
"""

import json
import subprocess
import sys

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

# Test tracking
passed = 0
failed = 0


def dfx_call(method: str, args: str = "()", identity: str = None) -> dict:
    """Call a canister method using dfx and return JSON result."""
    cmd = ["dfx", "canister", "call", "token_backend", method, args, "--output", "json"]
    if identity:
        cmd.extend(["--identity", identity])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"dfx call failed: {result.stderr}")
        return {"error": result.stderr}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def parse_nat(value):
    """Parse a nat value that may be a string with underscores or an int."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Only parse if it looks like a number (digits and underscores only)
        cleaned = value.replace("_", "")
        if cleaned.isdigit():
            return int(cleaned)
    return value


def get_principal(identity: str = None) -> str:
    """Get the principal for an identity."""
    cmd = ["dfx", "identity", "get-principal"]
    if identity:
        cmd.extend(["--identity", identity])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def assert_equals(expected, actual, test_name: str):
    """Assert equality and track results. Handles nat values with underscores."""
    global passed, failed
    # Normalize both values for comparison
    exp_normalized = (
        parse_nat(expected) if isinstance(expected, (int, str)) else expected
    )
    act_normalized = parse_nat(actual) if isinstance(actual, (int, str)) else actual

    if exp_normalized == act_normalized:
        print(f"{GREEN}✓ {test_name}{RESET}")
        passed += 1
        return True
    else:
        print(f"{RED}✗ {test_name}{RESET}")
        print(f"  Expected: {expected}")
        print(f"  Actual: {actual}")
        failed += 1
        return False


def assert_contains(haystack, needle: str, test_name: str):
    """Assert that haystack contains needle."""
    global passed, failed
    haystack_str = str(haystack)
    if needle in haystack_str:
        print(f"{GREEN}✓ {test_name}{RESET}")
        passed += 1
        return True
    else:
        print(f"{RED}✗ {test_name}{RESET}")
        print(f"  Expected to contain: {needle}")
        print(f"  Actual: {haystack_str}")
        failed += 1
        return False


def assert_true(condition: bool, test_name: str):
    """Assert condition is true."""
    global passed, failed
    if condition:
        print(f"{GREEN}✓ {test_name}{RESET}")
        passed += 1
        return True
    else:
        print(f"{RED}✗ {test_name}{RESET}")
        failed += 1
        return False


def run_tests():
    """Run all integration tests."""
    # Get principals
    deployer = get_principal()
    alice = get_principal("test_alice")
    bob = get_principal("test_bob")
    charlie = get_principal("test_charlie")

    print(f"Deployer: {deployer}")
    print(f"Alice: {alice}")
    print(f"Bob: {bob}")
    print(f"Charlie: {charlie}")
    print()

    # ==========================================
    # ICRC-1 Query Tests
    # ==========================================
    print("--- ICRC-1 Query Tests ---")

    result = dfx_call("icrc1_name")
    assert_equals("Simple Token", result, "icrc1_name returns correct name")

    result = dfx_call("icrc1_symbol")
    assert_equals("SMPL", result, "icrc1_symbol returns correct symbol")

    result = dfx_call("icrc1_decimals")
    assert_equals(8, result, "icrc1_decimals returns 8")

    result = dfx_call("icrc1_fee")
    assert_equals(10000, result, "icrc1_fee returns 10000")

    result = dfx_call("icrc1_total_supply")
    assert_equals(
        100000000000000000, result, "icrc1_total_supply returns initial supply"
    )

    result = dfx_call("is_test_mode")
    assert_equals(True, result, "is_test_mode returns true")

    # ==========================================
    # Balance Tests
    # ==========================================
    print()
    print("--- Balance Tests ---")

    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{deployer}"; subaccount = null }})',
    )
    assert_equals(100000000000000000, result, "deployer has initial supply")

    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_equals(0, result, "alice has zero balance initially")

    # ==========================================
    # Transfer Tests
    # ==========================================
    print()
    print("--- Transfer Tests ---")

    transfer_amount = 100000000  # 1 token
    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{alice}"; subaccount = null }}; amount = {transfer_amount} : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == True,
        "transfer from deployer to alice succeeds",
    )

    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_equals(transfer_amount, result, "alice has correct balance after transfer")

    # ==========================================
    # Subaccount Tests
    # ==========================================
    print()
    print("--- Subaccount Tests ---")

    # Use a simple subaccount blob
    subaccount_hex = "\\69\\6e\\76\\6f\\69\\63\\65\\31\\32\\33\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00\\00"
    subaccount_blob = f'blob "{subaccount_hex}"'

    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{bob}"; subaccount = opt {subaccount_blob} }}; amount = 50000000 : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == True,
        "transfer to subaccount succeeds",
    )

    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{bob}"; subaccount = opt {subaccount_blob} }})',
    )
    assert_equals(50000000, result, "subaccount has correct balance")

    # ==========================================
    # Insufficient Balance Tests
    # ==========================================
    print()
    print("--- Insufficient Balance Tests ---")

    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = 1000000 : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
        identity="test_charlie",
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == False,
        "transfer with insufficient balance fails",
    )
    assert_contains(
        result.get("error", ""),
        "Insufficient balance",
        "error message contains 'Insufficient balance'",
    )

    # ==========================================
    # Mint Tests (Test Mode)
    # ==========================================
    print()
    print("--- Mint Tests (Test Mode) ---")

    mint_amount = 500000000
    result = dfx_call(
        "mint",
        f'(record {{ to = record {{ owner = principal "{charlie}"; subaccount = null }}; amount = {mint_amount} : nat }})',
        identity="test_charlie",
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == True,
        "mint in test mode succeeds",
    )

    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{charlie}"; subaccount = null }})',
    )
    assert_equals(mint_amount, result, "charlie has minted tokens")

    # ==========================================
    # Transfer from Minted Tokens
    # ==========================================
    print()
    print("--- Transfer from Minted Tokens ---")

    charlie_transfer = 100000000
    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{alice}"; subaccount = null }}; amount = {charlie_transfer} : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
        identity="test_charlie",
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == True,
        "charlie can transfer minted tokens",
    )

    # Alice should now have 100_000_000 + 100_000_000 = 200_000_000
    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_equals(200000000, result, "alice received tokens from charlie")

    # ==========================================
    # Metadata Tests
    # ==========================================
    print()
    print("--- Metadata Tests ---")

    result = dfx_call("get_token_info")
    assert_true(isinstance(result, dict), "get_token_info returns dict")
    assert_equals("Simple Token", result.get("name"), "get_token_info has correct name")
    assert_equals("SMPL", result.get("symbol"), "get_token_info has correct symbol")

    result = dfx_call("get_owner")
    assert_equals(deployer, result, "get_owner returns deployer principal")

    # ==========================================
    # Transaction History Tests
    # ==========================================
    print()
    print("--- Transaction History Tests ---")

    result = dfx_call(
        "get_account_transactions",
        f'(record {{ account = record {{ owner = principal "{alice}"; subaccount = null }}; start = null; max_results = 10 : nat }})',
    )
    assert_true(
        "Ok" in str(result) or isinstance(result, dict),
        "get_account_transactions returns result",
    )

    result = dfx_call("get_transactions", "(0 : nat, 10 : nat)")
    assert_true(isinstance(result, dict), "get_transactions returns dict")
    assert_true(
        "transactions" in result or "transactions" in str(result),
        "get_transactions has transactions",
    )

    result = dfx_call("get_top_holders", "(5 : nat)")
    assert_true(
        isinstance(result, list) or "address" in str(result),
        "get_top_holders returns holders",
    )

    result = dfx_call("get_token_distribution")
    assert_true(isinstance(result, dict), "get_token_distribution returns dict")

    # ==========================================
    # Authority Operations: forced_transfer
    # ==========================================
    print()
    print("--- Authority forced_transfer Tests ---")

    def balance_of(principal):
        return parse_nat(
            dfx_call(
                "icrc1_balance_of",
                f'(record {{ owner = principal "{principal}"; subaccount = null }})',
            )
        )

    result = dfx_call("get_authority")
    assert_equals(deployer, result, "authority defaults to owner")

    alice_before = balance_of(alice)
    bob_before = balance_of(bob)
    forced_amount = 50000000

    # Deployer (owner = authority and controller) force-moves alice -> bob
    result = dfx_call(
        "forced_transfer",
        f'(record {{ from = record {{ owner = principal "{alice}"; subaccount = null }}; to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = {forced_amount} : nat; memo = opt "court order" }})',
    )
    assert_contains(result, "Ok", "authority forced_transfer succeeds")

    assert_equals(
        alice_before - forced_amount, balance_of(alice),
        "alice debited by forced_transfer (no fee)",
    )
    assert_equals(
        bob_before + forced_amount, balance_of(bob),
        "bob credited by forced_transfer",
    )

    # Non-authority cannot force-transfer
    result = dfx_call(
        "forced_transfer",
        f'(record {{ from = record {{ owner = principal "{bob}"; subaccount = null }}; to = record {{ owner = principal "{charlie}"; subaccount = null }}; amount = 1 : nat; memo = null }})',
        identity="test_charlie",
    )
    assert_contains(result, "Unauthorized", "non-authority forced_transfer fails")

    # Insufficient balance
    result = dfx_call(
        "forced_transfer",
        f'(record {{ from = record {{ owner = principal "{charlie}"; subaccount = null }}; to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = 999999999999999999 : nat; memo = null }})',
    )
    assert_contains(result, "InsufficientBalance", "forced_transfer beyond balance fails")

    # Same-account forced transfer rejected
    result = dfx_call(
        "forced_transfer",
        f'(record {{ from = record {{ owner = principal "{bob}"; subaccount = null }}; to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = 1 : nat; memo = null }})',
    )
    assert_contains(result, "InvalidRecipient", "forced_transfer to same account fails")

    # Audit trail
    result = dfx_call("get_transactions", "(0 : nat, 100 : nat)")
    txs = result.get("transactions", []) if isinstance(result, dict) else []
    kinds = [tx.get("kind") for tx in txs]
    assert_true("forced_transfer" in kinds, "forced_transfer logged in transaction history")

    # ==========================================
    # Authority Operations: freeze / unfreeze
    # ==========================================
    print()
    print("--- Authority freeze/unfreeze Tests ---")

    # Freeze alice
    result = dfx_call(
        "freeze_account",
        f'(record {{ account = record {{ owner = principal "{alice}"; subaccount = null }}; reason = opt "sanctions" }})',
    )
    assert_contains(result, "Ok", "authority freeze_account succeeds")

    result = dfx_call(
        "is_account_frozen",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_true(
        isinstance(result, dict) and result.get("frozen") == True,
        "is_account_frozen reports frozen",
    )
    assert_contains(result.get("reason", ""), "sanctions", "freeze reason is recorded")

    # Frozen account cannot send
    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = 1000 : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
        identity="test_alice",
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == False,
        "frozen account cannot send tokens",
    )
    assert_contains(result.get("error", ""), "frozen", "frozen transfer error mentions freeze")

    # Frozen account can still receive
    alice_frozen_balance = balance_of(alice)
    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{alice}"; subaccount = null }}; amount = 1000 : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == True,
        "frozen account can still receive tokens",
    )
    assert_equals(
        alice_frozen_balance + 1000, balance_of(alice),
        "frozen account balance credited",
    )

    # forced_transfer still works on frozen account
    result = dfx_call(
        "forced_transfer",
        f'(record {{ from = record {{ owner = principal "{alice}"; subaccount = null }}; to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = 1000 : nat; memo = null }})',
    )
    assert_contains(result, "Ok", "forced_transfer works on frozen account")

    # Non-authority cannot freeze or unfreeze
    result = dfx_call(
        "freeze_account",
        f'(record {{ account = record {{ owner = principal "{bob}"; subaccount = null }}; reason = null }})',
        identity="test_charlie",
    )
    assert_contains(result, "Unauthorized", "non-authority freeze fails")

    result = dfx_call(
        "unfreeze_account",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
        identity="test_charlie",
    )
    assert_contains(result, "Unauthorized", "non-authority unfreeze fails")

    # Unfreeze restores transfers
    result = dfx_call(
        "unfreeze_account",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_contains(result, "Ok", "authority unfreeze_account succeeds")

    result = dfx_call(
        "is_account_frozen",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_true(
        isinstance(result, dict) and result.get("frozen") == False,
        "is_account_frozen reports unfrozen",
    )

    result = dfx_call(
        "icrc1_transfer",
        f'(record {{ to = record {{ owner = principal "{bob}"; subaccount = null }}; amount = 1000 : nat; fee = null; memo = null; from_subaccount = null; created_at_time = null }})',
        identity="test_alice",
    )
    assert_true(
        isinstance(result, dict) and result.get("success") == True,
        "unfrozen account can send tokens again",
    )

    # Freeze/unfreeze appear in the transaction log
    result = dfx_call("get_transactions", "(0 : nat, 100 : nat)")
    txs = result.get("transactions", []) if isinstance(result, dict) else []
    kinds = [tx.get("kind") for tx in txs]
    assert_true("freeze" in kinds, "freeze logged in transaction history")
    assert_true("unfreeze" in kinds, "unfreeze logged in transaction history")

    # ==========================================
    # Authority Operations: transfer_authority
    # ==========================================
    print()
    print("--- Authority transfer_authority Tests ---")

    # Non-authority cannot hand over
    result = dfx_call(
        "transfer_authority",
        f'(record {{ new_authority = principal "{charlie}"; memo = null }})',
        identity="test_charlie",
    )
    assert_contains(result, "Unauthorized", "non-authority transfer_authority fails")

    # No-op handover rejected
    result = dfx_call(
        "transfer_authority",
        f'(record {{ new_authority = principal "{deployer}"; memo = null }})',
    )
    assert_contains(result, "InvalidRecipient", "no-op authority handover fails")

    # Authority hands over to alice
    result = dfx_call(
        "transfer_authority",
        f'(record {{ new_authority = principal "{alice}"; memo = opt "governance handover" }})',
    )
    assert_contains(result, "Ok", "authority handover succeeds")

    result = dfx_call("get_authority")
    assert_equals(alice, result, "get_authority returns new authority")

    # New authority (alice) can freeze
    result = dfx_call(
        "freeze_account",
        f'(record {{ account = record {{ owner = principal "{bob}"; subaccount = null }}; reason = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "new authority can freeze accounts")
    result = dfx_call(
        "unfreeze_account",
        f'(record {{ owner = principal "{bob}"; subaccount = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "new authority can unfreeze accounts")

    # Old authority (deployer) is still a controller, so retains powers;
    # but bob (neither authority nor controller) has none.
    result = dfx_call(
        "freeze_account",
        f'(record {{ account = record {{ owner = principal "{charlie}"; subaccount = null }}; reason = null }})',
        identity="test_bob",
    )
    assert_contains(result, "Unauthorized", "non-authority still cannot freeze")

    # Controller can hand authority back (recovery path)
    result = dfx_call(
        "transfer_authority",
        f'(record {{ new_authority = principal "{deployer}"; memo = null }})',
    )
    assert_contains(result, "Ok", "controller can recover authority")

    result = dfx_call("get_authority")
    assert_equals(deployer, result, "authority restored to deployer")

    # transfer_authority appears in the transaction log
    result = dfx_call("get_transactions", "(0 : nat, 100 : nat)")
    txs = result.get("transactions", []) if isinstance(result, dict) else []
    kinds = [tx.get("kind") for tx in txs]
    assert_true("transfer_authority" in kinds, "transfer_authority logged in transaction history")

    # ==========================================
    # Init args: custom metadata + initial_owner
    # (reinstalls the canister, so this section must stay last)
    # ==========================================
    print()
    print("--- Init Metadata / initial_owner Tests ---")

    reinstall_arg = (
        '(record { name = "Realm Coin"; symbol = "RLMC"; decimals = 6 : nat8; '
        "total_supply = 5000000 : nat; fee = 100 : nat; test = opt true; "
        f'initial_owner = opt principal "{alice}" }})'
    )
    result = subprocess.run(
        ["dfx", "deploy", "token_backend", "--mode", "reinstall",
         "--argument", reinstall_arg, "--yes"],
        capture_output=True, text=True,
    )
    assert_true(result.returncode == 0,
                f"reinstall with custom init args succeeds: {result.stderr[-300:]}")

    result = dfx_call("icrc1_name")
    assert_equals("Realm Coin", result, "icrc1_name reflects init args")
    result = dfx_call("icrc1_symbol")
    assert_equals("RLMC", result, "icrc1_symbol reflects init args")
    result = dfx_call("icrc1_decimals")
    assert_equals(6, result, "icrc1_decimals reflects init args")
    result = dfx_call("icrc1_fee")
    assert_equals(100, result, "icrc1_fee reflects init args")

    result = dfx_call("get_owner")
    assert_equals(alice, result, "initial_owner becomes ledger owner")
    result = dfx_call("get_authority")
    assert_equals(alice, result, "initial_owner is the default authority")
    result = dfx_call(
        "icrc1_balance_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_equals(5000000, result, "initial supply minted to initial_owner")

    # initial_owner (not a controller) has authority powers
    result = dfx_call(
        "freeze_account",
        f'(record {{ account = record {{ owner = principal "{bob}"; subaccount = null }}; reason = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "initial_owner can exercise authority ops")

    # ==========================================
    # Summary
    # ==========================================
    print()
    print("==========================================")
    total = passed + failed
    if failed == 0:
        print(f"  {GREEN}All {total} tests passed! ✓{RESET}")
        return 0
    else:
        print(f"  {RED}{failed}/{total} tests failed{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
