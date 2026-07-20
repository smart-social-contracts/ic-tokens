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
        f'(record {{ token_id = opt (1 : nat); owner = record {{ owner = principal "{alice}"; subaccount = null }}; metadata = opt vec {{ record {{ "name"; variant {{ Text = "Alice NFT" }} }} }} }})',
    )
    assert_contains(result, "Ok", "mint NFT #1 to alice succeeds")

    # Mint NFT #2 to bob
    result = dfx_call(
        "mint",
        f'(record {{ token_id = opt (2 : nat); owner = record {{ owner = principal "{bob}"; subaccount = null }}; metadata = opt vec {{ record {{ "name"; variant {{ Text = "Bob NFT" }} }} }} }})',
    )
    assert_contains(result, "Ok", "mint NFT #2 to bob succeeds")

    # Mint NFT #3 to alice
    result = dfx_call(
        "mint",
        f'(record {{ token_id = opt (3 : nat); owner = record {{ owner = principal "{alice}"; subaccount = null }}; metadata = null }})',
    )
    assert_contains(result, "Ok", "mint NFT #3 to alice succeeds")

    # Verify total supply
    result = dfx_call("icrc7_total_supply")
    assert_equals(3, result, "icrc7_total_supply is 3 after minting")

    # Try to mint duplicate token ID
    result = dfx_call(
        "mint",
        f'(record {{ token_id = opt (1 : nat); owner = record {{ owner = principal "{charlie}"; subaccount = null }}; metadata = null }})',
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
        f'(vec {{ record {{ spender_subaccount = null; from = record {{ owner = principal "{bob}"; subaccount = null }}; to = record {{ owner = principal "{charlie}"; subaccount = null }}; token_id = 2 : nat; memo = null; created_at_time = null }} }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "alice transfers NFT #2 from bob to charlie")

    # Verify ownership changed
    result = dfx_call("icrc7_owner_of", "(2 : nat)")
    assert_contains(result, charlie, "NFT #2 is now owned by charlie")

    # Transfer from without approval fails
    result = dfx_call(
        "icrc37_transfer_from",
        f'(vec {{ record {{ spender_subaccount = null; from = record {{ owner = principal "{charlie}"; subaccount = null }}; to = record {{ owner = principal "{alice}"; subaccount = null }}; token_id = 1 : nat; memo = null; created_at_time = null }} }})',
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
        f'(vec {{ record {{ spender_subaccount = null; from = record {{ owner = principal "{charlie}"; subaccount = null }}; to = record {{ owner = principal "{alice}"; subaccount = null }}; token_id = 1 : nat; memo = null; created_at_time = null }} }})',
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
    owned = [parse_nat(v) for v in result] if isinstance(result, list) else []
    assert_true(1 in owned and 3 in owned, "alice owns NFT #1 and #3")

    # Charlie should own NFT #2
    result = dfx_call(
        "icrc7_tokens_of",
        f'(record {{ owner = principal "{charlie}"; subaccount = null }}, null, null)',
    )
    owned = [parse_nat(v) for v in result] if isinstance(result, list) else []
    assert_true(2 in owned, "charlie owns NFT #2")

    # Bob should own nothing
    result = dfx_call(
        "icrc7_balance_of",
        f'(record {{ owner = principal "{bob}"; subaccount = null }})',
    )
    assert_equals(0, result, "bob has 0 NFTs after transfers")

    # ==========================================
    # Sequential Auto-Assigned Token IDs
    # ==========================================
    print()
    print("--- Sequential Auto-Assigned Token ID Tests ---")

    result = dfx_call(
        "mint",
        f'(record {{ token_id = null; owner = record {{ owner = principal "{bob}"; subaccount = null }}; metadata = null }})',
    )
    assert_contains(result, "Ok", "mint with auto-assigned token ID succeeds")
    auto_id_1 = parse_nat(result.get("Ok")) if isinstance(result, dict) else None
    assert_equals(4, auto_id_1, "auto-assigned token ID is sequential (4)")

    result = dfx_call(
        "mint",
        f'(record {{ token_id = null; owner = record {{ owner = principal "{bob}"; subaccount = null }}; metadata = null }})',
    )
    auto_id_2 = parse_nat(result.get("Ok")) if isinstance(result, dict) else None
    assert_equals(5, auto_id_2, "next auto-assigned token ID increments (5)")

    # Explicit ID above the counter pushes the counter forward
    result = dfx_call(
        "mint",
        f'(record {{ token_id = opt (100 : nat); owner = record {{ owner = principal "{bob}"; subaccount = null }}; metadata = null }})',
    )
    assert_contains(result, "Ok", "mint with explicit high token ID succeeds")

    result = dfx_call(
        "mint",
        f'(record {{ token_id = null; owner = record {{ owner = principal "{bob}"; subaccount = null }}; metadata = null }})',
    )
    auto_id_3 = parse_nat(result.get("Ok")) if isinstance(result, dict) else None
    assert_equals(101, auto_id_3, "auto-assigned ID continues after explicit high ID (101)")

    # ==========================================
    # Authority Operations: force_transfer
    # ==========================================
    print()
    print("--- Authority force_transfer Tests ---")

    # Token #4 was minted by the deployer (in test mode) and is owned by bob.
    # The deployer is a canister controller, so it can force-transfer.
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 4 : nat; to = record {{ owner = principal "{alice}"; subaccount = null }}; memo = opt "court order #42" }})',
    )
    assert_contains(result, "Ok", "controller force_transfer succeeds")

    result = dfx_call("icrc7_owner_of", "(4 : nat)")
    assert_contains(result, alice, "token #4 is owned by alice after force_transfer")

    # Non-authority caller cannot force_transfer
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 4 : nat; to = record {{ owner = principal "{charlie}"; subaccount = null }}; memo = null }})',
        identity="test_bob",
    )
    assert_contains(result, "Err", "non-authority force_transfer fails")
    assert_contains(result, "Unauthorized", "non-authority force_transfer is Unauthorized")

    result = dfx_call("icrc7_owner_of", "(4 : nat)")
    assert_contains(result, alice, "token #4 still owned by alice after failed force_transfer")

    # Force transfer of non-existent token fails
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 424242 : nat; to = record {{ owner = principal "{alice}"; subaccount = null }}; memo = null }})',
    )
    assert_contains(result, "NonExistingTokenId", "force_transfer of non-existent token fails")

    # Force transfer to the current owner fails
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 4 : nat; to = record {{ owner = principal "{alice}"; subaccount = null }}; memo = null }})',
    )
    assert_contains(result, "InvalidRecipient", "force_transfer to current owner fails")

    # Approvals are cleared by force_transfer: alice approves bob on #4, then force-transfer
    result = dfx_call(
        "icrc37_approve_tokens",
        f'(vec {{ record {{ token_id = 4 : nat; approval_info = record {{ spender = record {{ owner = principal "{bob}"; subaccount = null }}; from_subaccount = null; expires_at = null; memo = null; created_at_time = null }} }} }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "alice approves bob for token #4")

    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 4 : nat; to = record {{ owner = principal "{charlie}"; subaccount = null }}; memo = opt "reassignment" }})',
    )
    assert_contains(result, "Ok", "force_transfer of approved token succeeds")

    result = dfx_call(
        "icrc37_is_approved",
        f'(record {{ owner = principal "{bob}"; subaccount = null }}, null, 4 : nat)',
    )
    assert_true(result == False or result == "false" or str(result) == "False", "approval cleared after force_transfer")

    # Audit trail: force_transfer appears in the transaction log
    result = dfx_call("get_transactions", "(0 : nat, 100 : nat)")
    kinds = [tx.get("kind") for tx in result] if isinstance(result, list) else []
    assert_true("force_transfer" in kinds, "force_transfer logged in transaction history")

    # ==========================================
    # Authority Operations: freeze / unfreeze
    # ==========================================
    print()
    print("--- Authority freeze/unfreeze Tests ---")

    # Freeze token #4 (owned by charlie)
    result = dfx_call(
        "freeze_token",
        '(record { token_id = 4 : nat; reason = opt "ownership dispute" })',
    )
    assert_contains(result, "Ok", "controller freeze_token succeeds")

    result = dfx_call("is_token_frozen", "(4 : nat)")
    assert_true(result == True or str(result) == "True" or result == "true", "token #4 reports frozen")

    # Frozen token metadata includes frozen flag
    result = dfx_call("icrc7_token_metadata", "(4 : nat)")
    assert_contains(result, "frozen", "token metadata exposes frozen state")

    # Holder cannot transfer a frozen token
    result = dfx_call(
        "icrc7_transfer",
        f'(vec {{ record {{ from_subaccount = null; to = record {{ owner = principal "{alice}"; subaccount = null }}; token_id = 4 : nat; memo = null; created_at_time = null }} }})',
        identity="test_charlie",
    )
    assert_contains(result, "Err", "holder cannot transfer frozen token")
    assert_contains(result, "frozen", "frozen transfer error mentions freeze")

    # Approvals also cannot move a frozen token
    result = dfx_call(
        "icrc37_approve_tokens",
        f'(vec {{ record {{ token_id = 4 : nat; approval_info = record {{ spender = record {{ owner = principal "{alice}"; subaccount = null }}; from_subaccount = null; expires_at = null; memo = null; created_at_time = null }} }} }})',
        identity="test_charlie",
    )
    assert_contains(result, "Ok", "owner can still approve while frozen")

    result = dfx_call(
        "icrc37_transfer_from",
        f'(vec {{ record {{ spender_subaccount = null; from = record {{ owner = principal "{charlie}"; subaccount = null }}; to = record {{ owner = principal "{alice}"; subaccount = null }}; token_id = 4 : nat; memo = null; created_at_time = null }} }})',
        identity="test_alice",
    )
    assert_contains(result, "Err", "transfer_from blocked on frozen token")

    # Authority can still force_transfer a frozen token
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 4 : nat; to = record {{ owner = principal "{bob}"; subaccount = null }}; memo = opt "verdict executed" }})',
    )
    assert_contains(result, "Ok", "force_transfer works on frozen token")

    result = dfx_call("icrc7_owner_of", "(4 : nat)")
    assert_contains(result, bob, "frozen token #4 force-transferred to bob")

    # Non-authority cannot freeze or unfreeze
    result = dfx_call(
        "freeze_token",
        '(record { token_id = 1 : nat; reason = null })',
        identity="test_bob",
    )
    assert_contains(result, "Unauthorized", "non-authority freeze fails")

    result = dfx_call("unfreeze_token", "(4 : nat)", identity="test_bob")
    assert_contains(result, "Unauthorized", "non-authority unfreeze fails")

    # Unfreeze restores holder transfers
    result = dfx_call("unfreeze_token", "(4 : nat)")
    assert_contains(result, "Ok", "controller unfreeze_token succeeds")

    result = dfx_call("is_token_frozen", "(4 : nat)")
    assert_true(result == False or str(result) == "False" or result == "false", "token #4 no longer frozen")

    result = dfx_call(
        "icrc7_transfer",
        f'(vec {{ record {{ from_subaccount = null; to = record {{ owner = principal "{charlie}"; subaccount = null }}; token_id = 4 : nat; memo = null; created_at_time = null }} }})',
        identity="test_bob",
    )
    assert_contains(result, "Ok", "holder can transfer after unfreeze")

    # Freeze/unfreeze appear in the transaction log
    result = dfx_call("get_transactions", "(0 : nat, 200 : nat)")
    kinds = [tx.get("kind") for tx in result] if isinstance(result, list) else []
    assert_true("freeze" in kinds, "freeze logged in transaction history")
    assert_true("unfreeze" in kinds, "unfreeze logged in transaction history")

    # ==========================================
    # Authority scoping (authorized-minter authority)
    # ==========================================
    print()
    print("--- Authority Scoping Tests ---")

    # Authorize alice as a minter, have her mint a token: alice becomes its authority
    result = dfx_call("add_authorized_minter", f'("{alice}")')
    assert_contains(result, "true", "controller adds alice as authorized minter")

    result = dfx_call(
        "mint",
        f'(record {{ token_id = null; owner = record {{ owner = principal "{charlie}"; subaccount = null }}; metadata = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "authorized minter alice mints a token")
    alice_token = parse_nat(result.get("Ok")) if isinstance(result, dict) else None

    result = dfx_call("get_token_authority", f"({alice_token} : nat)")
    assert_contains(result, alice, "token authority recorded as alice")

    # Alice (authority) can force-transfer her token even though not a controller
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = {alice_token} : nat; to = record {{ owner = principal "{bob}"; subaccount = null }}; memo = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "authority (non-controller) force_transfer succeeds")

    # Bob (not the authority of token #1, minted by deployer) cannot force it even though
    # bob is not an authorized minter; and alice (authorized minter but not #1's authority)
    # also cannot force-transfer token #1.
    result = dfx_call(
        "force_transfer",
        f'(record {{ token_id = 1 : nat; to = record {{ owner = principal "{bob}"; subaccount = null }}; memo = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Unauthorized", "authorized minter cannot force other authority's token")

    # Revoking alice's minter status also revokes her authority powers
    result = dfx_call("remove_authorized_minter", f'("{alice}")')
    assert_contains(result, "true", "controller removes alice from authorized minters")

    result = dfx_call(
        "freeze_token",
        f'(record {{ token_id = {alice_token} : nat; reason = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Unauthorized", "revoked minter loses authority powers")

    # ==========================================
    # Authority Operations: transfer_authority
    # ==========================================
    print()
    print("--- Authority transfer_authority Tests ---")

    # Re-authorize alice as a minter for these tests
    result = dfx_call("add_authorized_minter", f'("{alice}")')
    assert_contains(result, "true", "controller re-adds alice as authorized minter")

    # Controller hands over authority of token #1 to alice
    result = dfx_call(
        "transfer_authority",
        f'(record {{ token_id = 1 : nat; new_authority = principal "{alice}"; memo = opt "governance handover" }})',
    )
    assert_contains(result, "Ok", "controller transfer_authority succeeds")

    result = dfx_call("get_token_authority", "(1 : nat)")
    assert_contains(result, alice, "token #1 authority is now alice")

    # New authority (alice, authorized minter) can freeze/unfreeze token #1
    result = dfx_call(
        "freeze_token",
        f'(record {{ token_id = 1 : nat; reason = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "new authority can freeze the token")
    result = dfx_call("unfreeze_token", "(1 : nat)", identity="test_alice")
    assert_contains(result, "Ok", "new authority can unfreeze the token")

    # Current authority (alice) hands token #1 over to bob
    result = dfx_call(
        "transfer_authority",
        f'(record {{ token_id = 1 : nat; new_authority = principal "{bob}"; memo = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Ok", "authority (non-controller) transfer_authority succeeds")

    result = dfx_call("get_token_authority", "(1 : nat)")
    assert_contains(result, bob, "token #1 authority is now bob")

    # Old authority (alice) has lost her powers over token #1
    result = dfx_call(
        "freeze_token",
        f'(record {{ token_id = 1 : nat; reason = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Unauthorized", "old authority loses freeze rights")
    result = dfx_call(
        "transfer_authority",
        f'(record {{ token_id = 1 : nat; new_authority = principal "{alice}"; memo = null }})',
        identity="test_alice",
    )
    assert_contains(result, "Unauthorized", "old authority cannot hand authority back to itself")

    # Bob is the authority but not an authorized minter: no powers until added
    result = dfx_call(
        "freeze_token",
        f'(record {{ token_id = 1 : nat; reason = null }})',
        identity="test_bob",
    )
    assert_contains(result, "Unauthorized", "authority without minter status has no powers")

    result = dfx_call("add_authorized_minter", f'("{bob}")')
    assert_contains(result, "true", "controller adds bob as authorized minter")
    result = dfx_call(
        "freeze_token",
        f'(record {{ token_id = 1 : nat; reason = null }})',
        identity="test_bob",
    )
    assert_contains(result, "Ok", "authority with minter status can freeze")
    result = dfx_call("unfreeze_token", "(1 : nat)", identity="test_bob")
    assert_contains(result, "Ok", "authority with minter status can unfreeze")

    # No-op handover is rejected
    result = dfx_call(
        "transfer_authority",
        f'(record {{ token_id = 1 : nat; new_authority = principal "{bob}"; memo = null }})',
        identity="test_bob",
    )
    assert_contains(result, "InvalidRecipient", "no-op authority handover fails")

    # Non-existing token
    result = dfx_call(
        "transfer_authority",
        f'(record {{ token_id = 999999 : nat; new_authority = principal "{alice}"; memo = null }})',
    )
    assert_contains(result, "NonExistingTokenId", "transfer_authority of non-existent token fails")

    # Unauthorized caller (charlie, no role at all)
    result = dfx_call(
        "transfer_authority",
        f'(record {{ token_id = 1 : nat; new_authority = principal "{charlie}"; memo = null }})',
        identity="test_charlie",
    )
    assert_contains(result, "Unauthorized", "stranger cannot transfer authority")

    # Audit trail: transfer_authority appears in the transaction log
    result = dfx_call("get_transactions", "(0 : nat, 500 : nat)")
    kinds = [tx.get("kind") for tx in result] if isinstance(result, list) else []
    assert_true("transfer_authority" in kinds, "transfer_authority logged in transaction history")

    # Cleanup: remove bob as minter again
    result = dfx_call("remove_authorized_minter", f'("{bob}")')
    assert_contains(result, "true", "controller removes bob from authorized minters")

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
