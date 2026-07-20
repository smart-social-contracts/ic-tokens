<script>
  import { Principal } from '@dfinity/principal';
  import { isAuthenticated, principal } from '$lib/stores/auth.js';
  import {
    metadataRows,
    tokenDisplayName,
    tokenSubtitle,
  } from '$lib/metadata.js';
  import AssetGeoMap from '$lib/components/AssetGeoMap.svelte';

  export let token = null;
  export let geo = null;
  export let geoLoading = false;
  export let authorizedMinters = [];
  export let onBack = () => {};
  export let onAction = () => {};

  let transferRecipient = '';
  let transferMemo = '';
  let forceRecipient = '';
  let freezeReason = token?.frozenReason || '';
  let authorityRecipient = '';
  let acting = false;
  let actionError = '';
  let actionSuccess = '';

  $: viewer = $principal;
  $: selectedIsOwner = token && viewer && token.owner === viewer;
  $: selectedIsAuthority =
    token && viewer && token.authority === viewer && authorizedMinters.includes(viewer);
  $: selectedCanTransfer = selectedIsOwner && token && !token.frozen;

  function parseAuthorityError(result) {
    if (!result || 'Ok' in result) return null;
    const err = result.Err || {};
    if ('Unauthorized' in err) return 'You are not authorized for this action.';
    if ('NonExistingTokenId' in err) return 'Token does not exist.';
    if ('InvalidRecipient' in err) return 'Invalid recipient.';
    if ('GenericError' in err) return err.GenericError?.message || 'Operation failed.';
    return 'Operation failed.';
  }

  function parseTransferError(result) {
    if (!result || 'Ok' in result) return null;
    const err = result.Err || {};
    if ('Unauthorized' in err) return 'Only the owner can transfer this asset.';
    if ('NonExistingTokenId' in err) return 'Token does not exist.';
    if ('InvalidRecipient' in err) return 'Invalid recipient.';
    if ('GenericError' in err) return err.GenericError?.message || 'Transfer failed.';
    return 'Transfer failed.';
  }

  async function runAction(fn) {
    acting = true;
    actionError = '';
    actionSuccess = '';
    try {
      await fn();
    } catch (e) {
      actionError = e.message || 'Action failed';
    } finally {
      acting = false;
    }
  }

  async function handleTransfer() {
    if (!selectedCanTransfer || !transferRecipient.trim()) return;
    await runAction(async () => {
      const result = await onAction('transfer', {
        token_id: BigInt(token.id),
        to: { owner: Principal.fromText(transferRecipient.trim()), subaccount: [] },
        memo: transferMemo.trim() ? [transferMemo.trim()] : [],
        from_subaccount: [],
        created_at_time: [],
      });
      const wrapped = result?.[0];
      const res = Array.isArray(wrapped) && wrapped.length ? wrapped[0] : wrapped;
      const err = parseTransferError(res);
      if (err) {
        actionError = err;
        return;
      }
      actionSuccess = `Asset #${token.id} transferred.`;
      transferRecipient = '';
      transferMemo = '';
    });
  }

  async function handleForceTransfer() {
    if (!selectedIsAuthority || !forceRecipient.trim()) return;
    await runAction(async () => {
      const result = await onAction('force_transfer', {
        token_id: BigInt(token.id),
        to: { owner: Principal.fromText(forceRecipient.trim()), subaccount: [] },
        memo: [],
      });
      const err = parseAuthorityError(result);
      if (err) {
        actionError = err;
        return;
      }
      actionSuccess = `Authority reassigned asset #${token.id}.`;
      forceRecipient = '';
    });
  }

  async function handleFreeze() {
    if (!selectedIsAuthority) return;
    await runAction(async () => {
      const result = await onAction('freeze_token', {
        token_id: BigInt(token.id),
        reason: freezeReason.trim() ? [freezeReason.trim()] : [],
      });
      const err = parseAuthorityError(result);
      if (err) {
        actionError = err;
        return;
      }
      actionSuccess = `Asset #${token.id} frozen.`;
    });
  }

  async function handleUnfreeze() {
    if (!selectedIsAuthority) return;
    await runAction(async () => {
      const result = await onAction('unfreeze_token', BigInt(token.id));
      const err = parseAuthorityError(result);
      if (err) {
        actionError = err;
        return;
      }
      actionSuccess = `Asset #${token.id} unfrozen.`;
    });
  }

  async function handleTransferAuthority() {
    if (!selectedIsAuthority || !authorityRecipient.trim()) return;
    await runAction(async () => {
      const result = await onAction('transfer_authority', {
        token_id: BigInt(token.id),
        new_authority: Principal.fromText(authorityRecipient.trim()),
        memo: [],
      });
      const err = parseAuthorityError(result);
      if (err) {
        actionError = err;
        return;
      }
      actionSuccess = `Guard authority updated for asset #${token.id}.`;
      authorityRecipient = '';
    });
  }
</script>

<div class="detail-page">
  <div class="detail-header">
    <button class="btn btn-secondary" on:click={onBack}>← Back to registry</button>
  </div>

  <div class="detail-card">
    <div class="detail-headline">
      <h1>{tokenDisplayName(token)}</h1>
      <p class="hint">{tokenSubtitle(token)}</p>
    </div>

    {#if actionSuccess}
      <div class="success-box">{actionSuccess}</div>
    {/if}
    {#if actionError}
      <div class="error-box">{actionError}</div>
    {/if}

    <div class="detail-grid">
      <div class="detail-row">
        <span class="detail-label">Token ID</span>
        <span class="detail-value">#{token.id}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Owner</span>
        <span class="detail-value">{token.owner}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Authority</span>
        <span class="detail-value">{token.authority || '—'}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Status</span>
        <span class="detail-value">
          {token.frozen ? `Frozen${token.frozenReason ? `: ${token.frozenReason}` : ''}` : 'Active'}
        </span>
      </div>
    </div>

    {#if metadataRows(token).length}
      <h3>Metadata</h3>
      <table class="metadata-table">
        <tbody>
          {#each metadataRows(token) as row}
            <tr>
              <td>{row.key}</td>
              <td>{row.value}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}

    {#if geoLoading}
      <div class="info-box">Loading geographic data…</div>
    {:else if geo && (geo.h3Indexes?.length || (geo.lat != null && geo.lng != null) || (geo.gridX != null && geo.gridY != null))}
      <AssetGeoMap {geo} label="Location" />
    {/if}

    {#if $isAuthenticated}
      <div class="section-divider"></div>

      {#if selectedCanTransfer}
        <h3>Transfer asset</h3>
        <div class="form-grid">
          <div>
            <label for="transferRecipient">Recipient principal</label>
            <input id="transferRecipient" bind:value={transferRecipient} />
          </div>
          <div>
            <label for="transferMemo">Memo (optional)</label>
            <input id="transferMemo" bind:value={transferMemo} />
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" disabled={acting} on:click={handleTransfer}>
            Transfer
          </button>
        </div>
      {:else if selectedIsOwner && token.frozen}
        <div class="info-box">This asset is frozen and cannot be transferred by the owner.</div>
      {/if}

      {#if selectedIsAuthority}
        <div class="section-divider"></div>
        <h3>Authority controls</h3>
        <p class="hint">
          Forced transfer, freeze, and authority handover are registry-level powers for this asset.
        </p>

        <div class="form-grid">
          <div>
            <label for="forceRecipient">Force transfer to</label>
            <input id="forceRecipient" bind:value={forceRecipient} />
          </div>
          <div>
            <label for="freezeReason">Freeze reason</label>
            <input id="freezeReason" bind:value={freezeReason} />
          </div>
          <div>
            <label for="authorityRecipient">New authority principal</label>
            <input id="authorityRecipient" bind:value={authorityRecipient} />
          </div>
        </div>

        <div class="btn-row">
          <button class="btn btn-danger" disabled={acting} on:click={handleForceTransfer}>
            Force transfer
          </button>
          {#if token.frozen}
            <button class="btn btn-secondary" disabled={acting} on:click={handleUnfreeze}>
              Unfreeze
            </button>
          {:else}
            <button class="btn btn-secondary" disabled={acting} on:click={handleFreeze}>
              Freeze
            </button>
          {/if}
          <button class="btn btn-secondary" disabled={acting} on:click={handleTransferAuthority}>
            Transfer authority
          </button>
        </div>
      {/if}
    {:else}
      <div class="info-box">Sign in with Internet Identity to manage this asset.</div>
    {/if}
  </div>
</div>

<style>
  .detail-page {
    max-width: 880px;
    margin: 0 auto;
    padding: 24px 0;
  }

  .detail-header {
    margin-bottom: 16px;
  }

  .detail-card {
    background: var(--color-bg-primary);
    border: 1px solid var(--color-border-primary);
    border-radius: var(--radius-md);
    padding: 24px;
  }

  .detail-headline {
    margin-bottom: 20px;
  }

  .detail-headline h1 {
    margin: 0 0 4px;
  }

  .detail-grid {
    display: grid;
    gap: 10px;
    margin: 16px 0;
  }

  .detail-row {
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--color-border-primary);
  }

  .detail-label {
    color: var(--color-text-tertiary);
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .detail-value {
    word-break: break-all;
  }

  h3 {
    margin: 24px 0 12px;
  }

  .metadata-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
  }

  .metadata-table td {
    padding: 8px 0;
    border-bottom: 1px solid var(--color-border-primary);
    vertical-align: top;
  }

  .metadata-table td:first-child {
    width: 34%;
    color: var(--color-text-tertiary);
  }

  .section-divider {
    height: 1px;
    background: var(--color-border-primary);
    margin: 20px 0;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
  }

  .form-grid label {
    display: block;
    font-size: 0.82rem;
    color: var(--color-text-tertiary);
    margin-bottom: 4px;
  }

  .form-grid input {
    width: 100%;
  }

  .btn-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }

  .info-box,
  .success-box,
  .error-box {
    margin: 12px 0;
  }

  .hint {
    color: var(--color-text-tertiary);
  }
</style>
