#!/usr/bin/env python3
"""
Integration tests for ICRC-7/ICRC-37 NFT backend.
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
    cmd = ["dfx", "canister", "call", "nft_backend", method, args, "--output", "json"]
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
    """Assert equality and track results."""
    global passed, failed
    exp_normalized = parse_nat(expected) if isinstance(expected, (int, str)) else expected
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
    # ICRC-7 Query Tests
    # ==========================================
    print("--- ICRC-7 Query Tests ---")

    result = dfx_call("icrc7_name")
    assert_equals("Test NFT Collection", result, "icrc7_name returns correct name")

    result = dfx_call("icrc7_symbol")
    assert_equals("TNFT", result, "icrc7_symbol returns correct symbol")

    result = dfx_call("icrc7_total_supply")
    assert_equals(0, result, "icrc7_total_supply is 0 initially")

    result = dfx_call("icrc7_supply_cap")
    assert_true(result is None or result == [] or "null" in str(result), "icrc7_supply_cap is null (no cap)")

    result = dfx_call("icrc7_supported_standards")
    assert_contains(result, "ICRC-7", "supported standards includes ICRC-7")
    assert_contains(result, "ICRC-37", "supported standards includes ICRC-37")

    # ==========================================
    # Mint Tests
    # ==========================================
    print()
    print("--- Mint Tests ---")

    # Mint NFT #1 to alice
    result = dfx_call(
        "mint",
        f'(record {{ token_id = 1 : nat; owner = record {{ owner = principal "{alice}"; subaccount = null }}; metadata = opt vec {{ record {{ "name"; variant {{ Text = "Alice NFT" }} }} }} }})',
    )
    assert_contains(result, "Ok", "mint NFT #1 to alice succeeds")

    # Mint NFT #2 to bob
    result = dfx_call(
        "mint",
        f'(record {{ token_id = 2 : nat; owner = record {{ owner = principal "{bob}"; subaccount = null }}; metadata = opt vec {{ record {{ "name"; variant {{ Text = "Bob NFT" }} }} }} }})',
    )
    assert_contains(result, "Ok", "mint NFT #2 to bob succeeds")

    # Mint NFT #3 to alice
    result = dfx_call(
        "mint",
        f'(record {{ token_id = 3 : nat; owner = record {{ owner = principal "{alice}"; subaccount = null }}; metadata = null }})',
    )
    assert_contains(result, "Ok", "mint NFT #3 to alice succeeds")

    # Verify total supply
    result = dfx_call("icrc7_total_supply")
    assert_equals(3, result, "icrc7_total_supply is 3 after minting")

    # Try to mint duplicate token ID
    result = dfx_call(
        "mint",
        f'(record {{ token_id = 1 : nat; owner = record {{ owner = principal "{charlie}"; subaccount = null }}; metadata = null }})',
    )
    assert_contains(result, "Err", "mint duplicate token ID fails")

    # ==========================================
    # Ownership Tests
    # ==========================================
    print()
    print("--- Ownership Tests ---")

    result = dfx_call("icrc7_owner_of", "(1 : nat)")
    assert_contains(result, alice, "NFT #1 is owned by alice")

    result = dfx_call("icrc7_owner_of", "(2 : nat)")
    assert_contains(result, bob, "NFT #2 is owned by bob")

    result = dfx_call("icrc7_owner_of", "(999 : nat)")
    assert_true(result is None or result == [] or "null" in str(result), "non-existent token returns null")

    # ==========================================
    # Balance Tests
    # ==========================================
    print()
    print("--- Balance Tests ---")

    result = dfx_call(
        "icrc7_balance_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }})',
    )
    assert_equals(2, result, "alice has 2 NFTs")

    result = dfx_call(
        "icrc7_balance_of",
        f'(record {{ owner = principal "{bob}"; subaccount = null }})',
    )
    assert_equals(1, result, "bob has 1 NFT")

    result = dfx_call(
        "icrc7_balance_of",
        f'(record {{ owner = principal "{charlie}"; subaccount = null }})',
    )
    assert_equals(0, result, "charlie has 0 NFTs")

    # ==========================================
    # Token Listing Tests
    # ==========================================
    print()
    print("--- Token Listing Tests ---")

    result = dfx_call("icrc7_tokens", "(null, null)")
    assert_true(isinstance(result, list), "icrc7_tokens returns a list")
    assert_true(len(result) == 3, "icrc7_tokens returns 3 tokens")

    result = dfx_call(
        "icrc7_tokens_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }}, null, null)',
    )
    assert_true(isinstance(result, list), "icrc7_tokens_of returns a list")
    assert_true(len(result) == 2, "alice owns 2 tokens")

    # ==========================================
    # Transfer Tests
    # ==========================================
    print()
    print("--- ICRC-7 Transfer Tests ---")

    # Alice transfers NFT #1 to charlie
    result = dfx_call(
        "icrc7_transfer",
        f'(vec {{ record {{ from_subaccount = null; to = record {{ owner = principal "{charlie}"; subaccount = null }}; token_id = 1 : nat; memo = null; created_at_time = null }} }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "alice transfers NFT #1 to charlie")

    # Verify ownership changed
    result = dfx_call("icrc7_owner_of", "(1 : nat)")
    assert_contains(result, charlie, "NFT #1 is now owned by charlie")

    # Try transfer without ownership (alice tries to transfer #2 which belongs to bob)
    result = dfx_call(
        "icrc7_transfer",
        f'(vec {{ record {{ from_subaccount = null; to = record {{ owner = principal "{charlie}"; subaccount = null }}; token_id = 2 : nat; memo = null; created_at_time = null }} }})',
        identity="test_alice",
    )
    assert_contains(result, "Err", "transfer without ownership fails")

    # ==========================================
    # ICRC-37 Approval Tests
    # ==========================================
    print()
    print("--- ICRC-37 Approval Tests ---")

    # Bob approves alice to transfer NFT #2
    result = dfx_call(
        "icrc37_approve_tokens",
        f'(vec {{ record {{ token_id = 2 : nat; approval_info = record {{ spender = record {{ owner = principal "{alice}"; subaccount = null }}; from_subaccount = null; expires_at = null; memo = null; created_at_time = null }} }} }})',
        identity="test_bob",
    )
    assert_contains(result, "Ok", "bob approves alice for NFT #2")

    # Check approval
    result = dfx_call(
        "icrc37_is_approved",
        f'(record {{ owner = principal "{alice}"; subaccount = null }}, null, 2 : nat)',
    )
    assert_true(result == True or result == "true" or str(result) == "True", "alice is approved for NFT #2")

    # Charlie is not approved
    result = dfx_call(
        "icrc37_is_approved",
        f'(record {{ owner = principal "{charlie}"; subaccount = null }}, null, 2 : nat)',
    )
    assert_true(result == False or result == "false" or str(result) == "False", "charlie is not approved for NFT #2")

    # ==========================================
    # ICRC-37 Transfer From Tests
    # ==========================================
    print()
    print("--- ICRC-37 Transfer From Tests ---")

    # Alice uses approval to transfer NFT #2 from bob to charlie
    result = dfx_call(
        "icrc37_transfer_from",
        f'(vec {{ record {{ spender_subaccount = null; from_ = record {{ owner = principal "{bob}"; subaccount = null }}; to = record {{ owner = principal "{charlie}"; subaccount = null }}; token_id = 2 : nat; memo = null; created_at_time = null }} }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "alice transfers NFT #2 from bob to charlie")

    # Verify ownership changed
    result = dfx_call("icrc7_owner_of", "(2 : nat)")
    assert_contains(result, charlie, "NFT #2 is now owned by charlie")

    # Transfer from without approval fails
    result = dfx_call(
        "icrc37_transfer_from",
        f'(vec {{ record {{ spender_subaccount = null; from_ = record {{ owner = principal "{charlie}"; subaccount = null }}; to = record {{ owner = principal "{alice}"; subaccount = null }}; token_id = 1 : nat; memo = null; created_at_time = null }} }})',
        identity="test_bob",
    )
    assert_contains(result, "Err", "transfer_from without approval fails")

    # ==========================================
    # Collection Approval Tests
    # ==========================================
    print()
    print("--- Collection Approval Tests ---")

    # Charlie approves deployer for all tokens
    result = dfx_call(
        "icrc37_approve_collection",
        f'(vec {{ record {{ approval_info = record {{ spender = record {{ owner = principal "{deployer}"; subaccount = null }}; from_subaccount = null; expires_at = null; memo = null; created_at_time = null }} }} }})',
        identity="test_charlie",
    )
    assert_contains(result, "Ok", "charlie approves deployer for collection")

    # Deployer can now transfer any of charlie's NFTs
    result = dfx_call(
        "icrc37_transfer_from",
        f'(vec {{ record {{ spender_subaccount = null; from_ = record {{ owner = principal "{charlie}"; subaccount = null }}; to = record {{ owner = principal "{alice}"; subaccount = null }}; token_id = 1 : nat; memo = null; created_at_time = null }} }})',
    )
    assert_contains(result, "Ok", "deployer transfers NFT #1 from charlie to alice using collection approval")

    # Verify ownership
    result = dfx_call("icrc7_owner_of", "(1 : nat)")
    assert_contains(result, alice, "NFT #1 is now owned by alice")

    # ==========================================
    # Transaction History Tests
    # ==========================================
    print()
    print("--- Transaction History Tests ---")

    result = dfx_call("get_transactions", "(0 : nat, 20 : nat)")
    assert_true(isinstance(result, list), "get_transactions returns a list")
    assert_true(len(result) > 0, "transaction history is not empty")

    # ==========================================
    # Final State Verification
    # ==========================================
    print()
    print("--- Final State Verification ---")

    # Alice should own NFT #1 and #3
    result = dfx_call(
        "icrc7_tokens_of",
        f'(record {{ owner = principal "{alice}"; subaccount = null }}, null, null)',
    )
    assert_true(1 in result and 3 in result, "alice owns NFT #1 and #3")

    # Charlie should own NFT #2
    result = dfx_call(
        "icrc7_tokens_of",
        f'(record {{ owner = principal "{charlie}"; subaccount = null }}, null, null)',
    )
    assert_true(2 in result, "charlie owns NFT #2")

    # Bob should own nothing
    result = dfx_call(
        "icrc7_balance_of",
        f'(record {{ owner = principal "{bob}"; subaccount = null }})',
    )
    assert_equals(0, result, "bob has 0 NFTs after transfers")

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
