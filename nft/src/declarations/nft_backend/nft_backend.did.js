export const idlFactory = ({ IDL }) => {
  const InitArg = IDL.Record({
    'supply_cap' : IDL.Opt(IDL.Nat),
    'name' : IDL.Text,
    'test' : IDL.Opt(IDL.Bool),
    'description' : IDL.Opt(IDL.Text),
    'symbol' : IDL.Text,
  });
  const TransactionRecord = IDL.Record({
    'id' : IDL.Nat,
    'to_principal' : IDL.Text,
    'spender_subaccount' : IDL.Text,
    'token_id' : IDL.Nat,
    'to_subaccount' : IDL.Text,
    'kind' : IDL.Text,
    'memo' : IDL.Text,
    'spender_principal' : IDL.Text,
    'from_subaccount' : IDL.Text,
    'from_principal' : IDL.Text,
    'timestamp' : IDL.Nat64,
  });
  const Account = IDL.Record({
    'owner' : IDL.Principal,
    'subaccount' : IDL.Opt(IDL.Vec(IDL.Nat8)),
  });
  const ApprovalInfo = IDL.Record({
    'memo' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'from_subaccount' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'created_at_time' : IDL.Opt(IDL.Nat64),
    'expires_at' : IDL.Opt(IDL.Nat64),
    'spender' : Account,
  });
  const ApproveCollectionArg = IDL.Record({ 'approval_info' : ApprovalInfo });
  const GenericError = IDL.Record({
    'message' : IDL.Text,
    'error_code' : IDL.Nat,
  });
  const CreatedInFutureError = IDL.Record({ 'ledger_time' : IDL.Nat64 });
  const ApproveCollectionError = IDL.Variant({
    'GenericError' : GenericError,
    'CreatedInFuture' : CreatedInFutureError,
    'GenericBatchError' : GenericError,
    'TooOld' : IDL.Null,
  });
  const ApproveCollectionResult = IDL.Variant({
    'Ok' : IDL.Nat,
    'Err' : ApproveCollectionError,
  });
  const ApproveTokenArg = IDL.Record({
    'token_id' : IDL.Nat,
    'approval_info' : ApprovalInfo,
  });
  const ApproveTokenError = IDL.Variant({
    'GenericError' : GenericError,
    'NonExistingTokenId' : IDL.Null,
    'Unauthorized' : IDL.Null,
    'CreatedInFuture' : CreatedInFutureError,
    'GenericBatchError' : GenericError,
    'TooOld' : IDL.Null,
  });
  const ApproveTokenResult = IDL.Variant({
    'Ok' : IDL.Nat,
    'Err' : ApproveTokenError,
  });
  const CollectionApproval = IDL.Record({ 'approval_info' : ApprovalInfo });
  const TokenApproval = IDL.Record({
    'token_id' : IDL.Nat,
    'approval_info' : ApprovalInfo,
  });
  const RevokeCollectionApprovalArg = IDL.Record({
    'memo' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'from_subaccount' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'created_at_time' : IDL.Opt(IDL.Nat64),
    'spender' : IDL.Opt(Account),
  });
  const RevokeCollectionApprovalError = IDL.Variant({
    'GenericError' : GenericError,
    'CreatedInFuture' : CreatedInFutureError,
    'ApprovalDoesNotExist' : IDL.Null,
    'GenericBatchError' : GenericError,
    'TooOld' : IDL.Null,
  });
  const RevokeCollectionApprovalResult = IDL.Variant({
    'Ok' : IDL.Nat,
    'Err' : RevokeCollectionApprovalError,
  });
  const RevokeTokenApprovalArg = IDL.Record({
    'token_id' : IDL.Nat,
    'memo' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'from_subaccount' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'created_at_time' : IDL.Opt(IDL.Nat64),
    'spender' : IDL.Opt(Account),
  });
  const RevokeTokenApprovalError = IDL.Variant({
    'GenericError' : GenericError,
    'NonExistingTokenId' : IDL.Null,
    'Unauthorized' : IDL.Null,
    'CreatedInFuture' : CreatedInFutureError,
    'ApprovalDoesNotExist' : IDL.Null,
    'GenericBatchError' : GenericError,
    'TooOld' : IDL.Null,
  });
  const RevokeTokenApprovalResult = IDL.Variant({
    'Ok' : IDL.Nat,
    'Err' : RevokeTokenApprovalError,
  });
  const TransferFromArg = IDL.Record({
    'to' : Account,
    'spender_subaccount' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'token_id' : IDL.Nat,
    'from' : Account,
    'memo' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'created_at_time' : IDL.Opt(IDL.Nat64),
  });
  const DuplicateError = IDL.Record({ 'duplicate_of' : IDL.Nat });
  const TransferFromError = IDL.Variant({
    'GenericError' : GenericError,
    'Duplicate' : DuplicateError,
    'NonExistingTokenId' : IDL.Null,
    'Unauthorized' : IDL.Null,
    'CreatedInFuture' : CreatedInFutureError,
    'InvalidRecipient' : IDL.Null,
    'GenericBatchError' : GenericError,
    'TooOld' : IDL.Null,
  });
  const TransferFromResult = IDL.Variant({
    'Ok' : IDL.Nat,
    'Err' : TransferFromError,
  });
  const MetadataValue = IDL.Variant({
    'Int' : IDL.Int,
    'Nat' : IDL.Nat,
    'Blob' : IDL.Vec(IDL.Nat8),
    'Text' : IDL.Text,
  });
  const StandardRecord = IDL.Record({ 'url' : IDL.Text, 'name' : IDL.Text });
  const TransferArg = IDL.Record({
    'to' : Account,
    'token_id' : IDL.Nat,
    'memo' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'from_subaccount' : IDL.Opt(IDL.Vec(IDL.Nat8)),
    'created_at_time' : IDL.Opt(IDL.Nat64),
  });
  const TransferError = IDL.Variant({
    'GenericError' : GenericError,
    'Duplicate' : DuplicateError,
    'NonExistingTokenId' : IDL.Null,
    'Unauthorized' : IDL.Null,
    'CreatedInFuture' : CreatedInFutureError,
    'InvalidRecipient' : IDL.Null,
    'GenericBatchError' : GenericError,
    'TooOld' : IDL.Null,
  });
  const TransferResult = IDL.Variant({ 'Ok' : IDL.Nat, 'Err' : TransferError });
  const MintArg = IDL.Record({
    'token_id' : IDL.Nat,
    'owner' : Account,
    'metadata' : IDL.Opt(IDL.Vec(IDL.Tuple(IDL.Text, MetadataValue))),
  });
  const MintError = IDL.Variant({
    'GenericError' : GenericError,
    'SupplyCapReached' : IDL.Null,
    'Unauthorized' : IDL.Null,
    'TokenIdAlreadyExists' : IDL.Null,
  });
  const MintResult = IDL.Variant({ 'Ok' : IDL.Nat, 'Err' : MintError });
  return IDL.Service({
    'get_transactions' : IDL.Func(
        [IDL.Nat, IDL.Nat],
        [IDL.Vec(TransactionRecord)],
        ['query'],
      ),
    'icrc37_approve_collection' : IDL.Func(
        [IDL.Vec(ApproveCollectionArg)],
        [IDL.Vec(IDL.Opt(ApproveCollectionResult))],
        [],
      ),
    'icrc37_approve_tokens' : IDL.Func(
        [IDL.Vec(ApproveTokenArg)],
        [IDL.Vec(IDL.Opt(ApproveTokenResult))],
        [],
      ),
    'icrc37_get_collection_approvals' : IDL.Func(
        [Account, IDL.Opt(Account), IDL.Opt(IDL.Nat)],
        [IDL.Vec(CollectionApproval)],
        ['query'],
      ),
    'icrc37_get_token_approvals' : IDL.Func(
        [IDL.Nat, IDL.Opt(Account), IDL.Opt(IDL.Nat)],
        [IDL.Vec(TokenApproval)],
        ['query'],
      ),
    'icrc37_is_approved' : IDL.Func(
        [Account, IDL.Opt(IDL.Vec(IDL.Nat8)), IDL.Nat],
        [IDL.Bool],
        ['query'],
      ),
    'icrc37_revoke_collection_approvals' : IDL.Func(
        [IDL.Vec(RevokeCollectionApprovalArg)],
        [IDL.Vec(IDL.Opt(RevokeCollectionApprovalResult))],
        [],
      ),
    'icrc37_revoke_token_approvals' : IDL.Func(
        [IDL.Vec(RevokeTokenApprovalArg)],
        [IDL.Vec(IDL.Opt(RevokeTokenApprovalResult))],
        [],
      ),
    'icrc37_transfer_from' : IDL.Func(
        [IDL.Vec(TransferFromArg)],
        [IDL.Vec(IDL.Opt(TransferFromResult))],
        [],
      ),
    'icrc7_balance_of' : IDL.Func([Account], [IDL.Nat], ['query']),
    'icrc7_collection_metadata' : IDL.Func(
        [],
        [IDL.Vec(IDL.Tuple(IDL.Text, MetadataValue))],
        ['query'],
      ),
    'icrc7_description' : IDL.Func([], [IDL.Opt(IDL.Text)], ['query']),
    'icrc7_name' : IDL.Func([], [IDL.Text], ['query']),
    'icrc7_owner_of' : IDL.Func([IDL.Nat], [IDL.Opt(Account)], ['query']),
    'icrc7_supply_cap' : IDL.Func([], [IDL.Opt(IDL.Nat)], ['query']),
    'icrc7_supported_standards' : IDL.Func(
        [],
        [IDL.Vec(StandardRecord)],
        ['query'],
      ),
    'icrc7_symbol' : IDL.Func([], [IDL.Text], ['query']),
    'icrc7_token_metadata' : IDL.Func(
        [IDL.Nat],
        [IDL.Opt(IDL.Vec(IDL.Tuple(IDL.Text, MetadataValue)))],
        ['query'],
      ),
    'icrc7_tokens' : IDL.Func(
        [IDL.Opt(IDL.Nat), IDL.Opt(IDL.Nat)],
        [IDL.Vec(IDL.Nat)],
        ['query'],
      ),
    'icrc7_tokens_of' : IDL.Func(
        [Account, IDL.Opt(IDL.Nat), IDL.Opt(IDL.Nat)],
        [IDL.Vec(IDL.Nat)],
        ['query'],
      ),
    'icrc7_total_supply' : IDL.Func([], [IDL.Nat], ['query']),
    'icrc7_transfer' : IDL.Func(
        [IDL.Vec(TransferArg)],
        [IDL.Vec(IDL.Opt(TransferResult))],
        [],
      ),
    'is_test_mode' : IDL.Func([], [IDL.Bool], ['query']),
    'mint' : IDL.Func([MintArg], [MintResult], []),
  });
};
export const init = ({ IDL }) => {
  const InitArg = IDL.Record({
    'supply_cap' : IDL.Opt(IDL.Nat),
    'name' : IDL.Text,
    'test' : IDL.Opt(IDL.Bool),
    'description' : IDL.Opt(IDL.Text),
    'symbol' : IDL.Text,
  });
  return [InitArg];
};
