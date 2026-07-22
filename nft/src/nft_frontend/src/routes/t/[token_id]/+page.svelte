<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { Principal } from '@dfinity/principal';
  import { getBackend } from '$lib/canisters.js';
  import { isAuthenticated } from '$lib/stores/auth.js';
  import {
    metaText,
    normalizeTokenMetadata,
  } from '$lib/metadata.js';
  import {
    extractGeoFromMetadata,
    resolveTokenGeo,
  } from '$lib/geo.js';
  import AssetDetail from '$lib/components/AssetDetail.svelte';

  let loading = true;
  let error = '';
  let token = null;
  let geo = null;
  let geoLoading = false;
  let authorizedMinters = [];
  let actor = null;
  let actionSuccess = '';
  let actionError = '';

  $: tokenIdParam = $page.params.token_id;
  $: tokenId = Number(tokenIdParam);

  onMount(async () => {
    await loadToken();
  });

  async function loadToken() {
    try {
      loading = true;
      error = '';
      actor = getBackend();
      if (!actor) {
        error = 'Backend not ready. Please refresh.';
        return;
      }
      if (!Number.isFinite(tokenId) || tokenId < 0) {
        error = `Invalid token ID: ${tokenIdParam}`;
        return;
      }

      const [owner, tokenMetadata, frozen, authorityOpt, minters] = await Promise.all([
        actor.icrc7_owner_of(BigInt(tokenId)).catch(() => []),
        actor.icrc7_token_metadata(BigInt(tokenId)).catch(() => []),
        actor.is_token_frozen(BigInt(tokenId)).catch(() => false),
        actor.get_token_authority(BigInt(tokenId)).catch(() => []),
        actor.list_authorized_minters().catch(() => []),
      ]);

      if (!owner || owner.length === 0) {
        error = `Asset #${tokenId} not found.`;
        return;
      }

      const authority = Array.isArray(authorityOpt) && authorityOpt.length ? authorityOpt[0] : '';
      const metadata = normalizeTokenMetadata(tokenMetadata);
      authorizedMinters = minters || [];
      token = {
        id: tokenId,
        owner: owner[0].owner.toText(),
        metadata,
        frozen: !!frozen,
        frozenReason: metaText(metadata, 'frozen_reason'),
        authority,
      };

      geo = extractGeoFromMetadata(metadata);
      geoLoading = true;
      try {
        geo = await resolveTokenGeo(metadata);
      } finally {
        geoLoading = false;
      }
    } catch (e) {
      console.error('Failed to load token:', e);
      error = e.message || 'Failed to load asset details.';
    } finally {
      loading = false;
    }
  }

  async function handleAction(action, payload) {
    if (!actor) throw new Error('Backend not ready');
    if (!$isAuthenticated) throw new Error('Please sign in first');
    switch (action) {
      case 'transfer':
        return await actor.icrc7_transfer([payload]);
      case 'force_transfer':
        return await actor.force_transfer(payload);
      case 'freeze_token':
        return await actor.freeze_token(payload);
      case 'unfreeze_token':
        return await actor.unfreeze_token(payload);
      case 'transfer_authority':
        return await actor.transfer_authority(payload);
      default:
        throw new Error(`Unknown action: ${action}`);
    }
  }

  async function onAction(action, payload) {
    const result = await handleAction(action, payload);
    if (action === 'transfer' && result?.[0]) {
      const res = result[0];
      const ok = Array.isArray(res) && res.length ? res[0] : res;
      if ('Ok' in ok || 'ok' in ok) {
        actionSuccess = `Asset #${tokenId} transferred.`;
        await loadToken();
      }
      return result;
    }
    const err = result?.Err;
    if (!err) {
      actionSuccess = 'Action completed.';
      await loadToken();
    }
    return result;
  }

  function goBack() {
    goto('/');
  }
</script>

<svelte:head>
  <title>{token ? `Asset #${token.id}` : 'Asset'} — Realms Registry</title>
</svelte:head>

{#if actionSuccess}
  <div class="success-box">{actionSuccess}</div>
{/if}
{#if actionError}
  <div class="error-box">{actionError}</div>
{/if}

{#if loading}
  <div class="loading">Loading asset…</div>
{:else if error}
  <div class="error-box">{error}</div>
{:else if token}
  <AssetDetail
    {token}
    {geo}
    geoLoading={geoLoading}
    {authorizedMinters}
    onBack={goBack}
    onAction={onAction}
  />
{/if}

<style>
  .loading,
  .success-box,
  .error-box {
    margin: 16px 0;
  }
</style>
