import type { Principal } from '@dfinity/principal';
import type { ActorMethod } from '@dfinity/agent';
import type { IDL } from '@dfinity/candid';

export interface Account {
  'owner' : Principal,
  'subaccount' : [] | [Uint8Array | number[]],
}
export interface ApprovalInfo {
  'memo' : [] | [Uint8Array | number[]],
  'from_subaccount' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [bigint],
  'expires_at' : [] | [bigint],
  'spender' : Account,
}
export interface ApproveCollectionArg { 'approval_info' : ApprovalInfo }
export type ApproveCollectionError = { 'GenericError' : GenericError } |
  { 'CreatedInFuture' : CreatedInFutureError } |
  { 'GenericBatchError' : GenericError } |
  { 'TooOld' : null };
export type ApproveCollectionResult = { 'Ok' : bigint } |
  { 'Err' : ApproveCollectionError };
export interface ApproveTokenArg {
  'token_id' : bigint,
  'approval_info' : ApprovalInfo,
}
export type ApproveTokenError = { 'GenericError' : GenericError } |
  { 'NonExistingTokenId' : null } |
  { 'Unauthorized' : null } |
  { 'CreatedInFuture' : CreatedInFutureError } |
  { 'GenericBatchError' : GenericError } |
  { 'TooOld' : null };
export type ApproveTokenResult = { 'Ok' : bigint } |
  { 'Err' : ApproveTokenError };
export interface CollectionApproval { 'approval_info' : ApprovalInfo }
export interface CreatedInFutureError { 'ledger_time' : bigint }
export interface DuplicateError { 'duplicate_of' : bigint }
export interface GenericError { 'message' : string, 'error_code' : bigint }
export interface InitArg {
  'supply_cap' : [] | [bigint],
  'name' : string,
  'test' : [] | [boolean],
  'description' : [] | [string],
  'symbol' : string,
}
export type MetadataValue = { 'Int' : bigint } |
  { 'Nat' : bigint } |
  { 'Blob' : Uint8Array | number[] } |
  { 'Text' : string };
export interface MintArg {
  'token_id' : bigint,
  'owner' : Account,
  'metadata' : [] | [Array<[string, MetadataValue]>],
}
export type MintError = { 'GenericError' : GenericError } |
  { 'SupplyCapReached' : null } |
  { 'Unauthorized' : null } |
  { 'TokenIdAlreadyExists' : null };
export type MintResult = { 'Ok' : bigint } |
  { 'Err' : MintError };
export interface RevokeCollectionApprovalArg {
  'memo' : [] | [Uint8Array | number[]],
  'from_subaccount' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [bigint],
  'spender' : [] | [Account],
}
export type RevokeCollectionApprovalError = { 'GenericError' : GenericError } |
  { 'CreatedInFuture' : CreatedInFutureError } |
  { 'ApprovalDoesNotExist' : null } |
  { 'GenericBatchError' : GenericError } |
  { 'TooOld' : null };
export type RevokeCollectionApprovalResult = { 'Ok' : bigint } |
  { 'Err' : RevokeCollectionApprovalError };
export interface RevokeTokenApprovalArg {
  'token_id' : bigint,
  'memo' : [] | [Uint8Array | number[]],
  'from_subaccount' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [bigint],
  'spender' : [] | [Account],
}
export type RevokeTokenApprovalError = { 'GenericError' : GenericError } |
  { 'NonExistingTokenId' : null } |
  { 'Unauthorized' : null } |
  { 'CreatedInFuture' : CreatedInFutureError } |
  { 'ApprovalDoesNotExist' : null } |
  { 'GenericBatchError' : GenericError } |
  { 'TooOld' : null };
export type RevokeTokenApprovalResult = { 'Ok' : bigint } |
  { 'Err' : RevokeTokenApprovalError };
export interface StandardRecord { 'url' : string, 'name' : string }
export interface TokenApproval {
  'token_id' : bigint,
  'approval_info' : ApprovalInfo,
}
export interface TransactionRecord {
  'id' : bigint,
  'to_principal' : string,
  'spender_subaccount' : string,
  'token_id' : bigint,
  'to_subaccount' : string,
  'kind' : string,
  'memo' : string,
  'spender_principal' : string,
  'from_subaccount' : string,
  'from_principal' : string,
  'timestamp' : bigint,
}
export interface TransferArg {
  'to' : Account,
  'token_id' : bigint,
  'memo' : [] | [Uint8Array | number[]],
  'from_subaccount' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [bigint],
}
export type TransferError = { 'GenericError' : GenericError } |
  { 'Duplicate' : DuplicateError } |
  { 'NonExistingTokenId' : null } |
  { 'Unauthorized' : null } |
  { 'CreatedInFuture' : CreatedInFutureError } |
  { 'InvalidRecipient' : null } |
  { 'GenericBatchError' : GenericError } |
  { 'TooOld' : null };
export interface TransferFromArg {
  'to' : Account,
  'spender_subaccount' : [] | [Uint8Array | number[]],
  'token_id' : bigint,
  'from' : Account,
  'memo' : [] | [Uint8Array | number[]],
  'created_at_time' : [] | [bigint],
}
export type TransferFromError = { 'GenericError' : GenericError } |
  { 'Duplicate' : DuplicateError } |
  { 'NonExistingTokenId' : null } |
  { 'Unauthorized' : null } |
  { 'CreatedInFuture' : CreatedInFutureError } |
  { 'InvalidRecipient' : null } |
  { 'GenericBatchError' : GenericError } |
  { 'TooOld' : null };
export type TransferFromResult = { 'Ok' : bigint } |
  { 'Err' : TransferFromError };
export type TransferResult = { 'Ok' : bigint } |
  { 'Err' : TransferError };
export interface _SERVICE {
  'get_transactions' : ActorMethod<[bigint, bigint], Array<TransactionRecord>>,
  'icrc37_approve_collection' : ActorMethod<
    [Array<ApproveCollectionArg>],
    Array<[] | [ApproveCollectionResult]>
  >,
  'icrc37_approve_tokens' : ActorMethod<
    [Array<ApproveTokenArg>],
    Array<[] | [ApproveTokenResult]>
  >,
  'icrc37_get_collection_approvals' : ActorMethod<
    [Account, [] | [Account], [] | [bigint]],
    Array<CollectionApproval>
  >,
  'icrc37_get_token_approvals' : ActorMethod<
    [bigint, [] | [Account], [] | [bigint]],
    Array<TokenApproval>
  >,
  'icrc37_is_approved' : ActorMethod<
    [Account, [] | [Uint8Array | number[]], bigint],
    boolean
  >,
  'icrc37_revoke_collection_approvals' : ActorMethod<
    [Array<RevokeCollectionApprovalArg>],
    Array<[] | [RevokeCollectionApprovalResult]>
  >,
  'icrc37_revoke_token_approvals' : ActorMethod<
    [Array<RevokeTokenApprovalArg>],
    Array<[] | [RevokeTokenApprovalResult]>
  >,
  'icrc37_transfer_from' : ActorMethod<
    [Array<TransferFromArg>],
    Array<[] | [TransferFromResult]>
  >,
  'icrc7_balance_of' : ActorMethod<[Account], bigint>,
  'icrc7_collection_metadata' : ActorMethod<[], Array<[string, MetadataValue]>>,
  'icrc7_description' : ActorMethod<[], [] | [string]>,
  'icrc7_name' : ActorMethod<[], string>,
  'icrc7_owner_of' : ActorMethod<[bigint], [] | [Account]>,
  'icrc7_supply_cap' : ActorMethod<[], [] | [bigint]>,
  'icrc7_supported_standards' : ActorMethod<[], Array<StandardRecord>>,
  'icrc7_symbol' : ActorMethod<[], string>,
  'icrc7_token_metadata' : ActorMethod<
    [bigint],
    [] | [Array<[string, MetadataValue]>]
  >,
  'icrc7_tokens' : ActorMethod<[[] | [bigint], [] | [bigint]], Array<bigint>>,
  'icrc7_tokens_of' : ActorMethod<
    [Account, [] | [bigint], [] | [bigint]],
    Array<bigint>
  >,
  'icrc7_total_supply' : ActorMethod<[], bigint>,
  'icrc7_transfer' : ActorMethod<
    [Array<TransferArg>],
    Array<[] | [TransferResult]>
  >,
  'is_test_mode' : ActorMethod<[], boolean>,
  'mint' : ActorMethod<[MintArg], MintResult>,
}
export declare const idlFactory: IDL.InterfaceFactory;
export declare const init: (args: { IDL: typeof IDL }) => IDL.Type[];
