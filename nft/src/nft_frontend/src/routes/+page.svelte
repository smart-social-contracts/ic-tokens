<script>
  import { onMount } from 'svelte';
  import { Principal } from '@dfinity/principal';
  import { getBackend } from '$lib/canisters.js';
  import { isAuthenticated, principal } from '$lib/stores/auth.js';
  import {
    metaText,
    normalizeTokenMetadata,
    tokenDisplayName,
    tokenSubtitle,
    truncate,
  } from '$lib/metadata.js';
  import AssetGeoMap from '$lib/components/AssetGeoMap.svelte';
  import {
    extractGeoFromMetadata,
    hasGeoMetadata,
    resolveTokenGeo,
  } from '$lib/geo.js';

  let loading = true;
  let error = null;
  let actionError = '';
  let actionSuccess = '';

  let collectionName = '';
  let collectionSymbol = '';
  let collectionDescription = '';
  let totalSupply = 0;
  let supplyCap = null;
  let testMode = false;
  let authorizedMinters = [];

  let tokens = [];
  let transactions = [];

  let mintOwner = '';
  let mintName = '';
  let mintAssetType = '';
  let minting = false;

  $: viewer = $principal;
  $: canMint = $isAuthenticated && authorizedMinters.includes(viewer);

  onMount(async () => {
    await loadData();
  });

  async function backend() {
    return getBackend();
  }

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

  function metaTextFromList(metadata, key) {
    return metaText(metadata, key);
  }

  async function enrichTokenGeo(token) {
    const geo = await resolveTokenGeo(token.metadata);
    return { ...token, geo };
  }

  async function loadData() {
    try {
      loading = true;
      error = null;
      actionError = '';
      const actor = await backend();

      const [name, symbol, supply, cap, test, minters, metadata] = await Promise.all([
        actor.icrc7_name(),
        actor.icrc7_symbol(),
        actor.icrc7_total_supply(),
        actor.icrc7_supply_cap(),
        actor.is_test_mode().catch(() => false),
        actor.list_authorized_minters().catch(() => []),
        actor.icrc7_collection_metadata().catch(() => []),
      ]);

      collectionName = name;
      collectionSymbol = symbol;
      totalSupply = Number(supply);
      supplyCap = cap && cap.length > 0 ? Number(cap[0]) : null;
      testMode = !!test;
      authorizedMinters = minters || [];
      collectionDescription =
        metadata.find((entry) => entry[0] === 'icrc7:description')?.[1]?.Text || '';

      const tokenIds = await actor.icrc7_tokens([], []);
      tokens = await Promise.all(
        tokenIds.slice(0, 40).map(async (id) => {
          const [owner, tokenMetadata, frozen, authorityOpt] = await Promise.all([
            actor.icrc7_owner_of(id),
            actor.icrc7_token_metadata(id).catch(() => []),
            actor.is_token_frozen(id).catch(() => false),
            actor.get_token_authority(id).catch(() => []),
          ]);
          const authority = Array.isArray(authorityOpt) && authorityOpt.length
            ? authorityOpt[0]
            : '';
          return {
            id: Number(id),
            owner:
              owner && owner.length > 0 ? owner[0].owner.toText() : 'Unknown',
            metadata: normalizeTokenMetadata(tokenMetadata),
            frozen: !!frozen,
            frozenReason: metaTextFromList(tokenMetadata, 'frozen_reason'),
            authority,
            geo: extractGeoFromMetadata(normalizeTokenMetadata(tokenMetadata)),
          };
        }),
      );

      tokens = await Promise.all(
        tokens.map(async (token) => {
          if (!hasGeoMetadata(token.metadata)) return token;
          return enrichTokenGeo(token);
        }),
      );

      const txs = await actor.get_transactions(0n, 12n);
      transactions = (txs || []).map((tx) => ({
        id: Number(tx.id),
        kind: tx.kind,
        tokenId: Number(tx.token_id),
        from: tx.from_principal || '—',
        to: tx.to_principal || '—',
        timestamp: tx.timestamp,
      }));
    } catch (e) {
      console.error('Failed to load registry data:', e);
      error = e.message || 'Failed to load registry data';
    } finally {
      loading = false;
    }
  }

  async function handleMint() {
    if (!canMint) {
      actionError = 'Only authorized minters can mint new assets.';
      return;
    }
    minting = true;
    actionError = '';
    actionSuccess = '';
    try {
      const actor = await backend();
      const ownerPrincipal = mintOwner?.trim() || viewer;
      const metadataEntries = [];
      if (mintName.trim()) metadataEntries.push(['name', { Text: mintName.trim() }]);
      if (mintAssetType.trim()) {
        metadataEntries.push(['asset_type', { Text: mintAssetType.trim() }]);
      }

      const result = await actor.mint({
        token_id: [],
        owner: {
          owner: Principal.fromText(ownerPrincipal),
          subaccount: [],
        },
        metadata: metadataEntries.length ? [metadataEntries] : [],
      });

      if ('Ok' in result) {
        actionSuccess = `Asset #${Number(result.Ok)} minted successfully.`;
        mintOwner = '';
        mintName = '';
        mintAssetType = '';
        await loadData();
      } else {
        actionError = parseAuthorityError(result) || 'Mint failed.';
      }
    } catch (e) {
      actionError = e.message || 'Mint failed.';
    } finally {
      minting = false;
    }
  }

  function openToken(token) {
    window.location.href = `/t/${token.id}`;
  }

  function formatTime(timestamp) {
    if (!timestamp) return '—';
    try {
      return new Date(Number(timestamp) / 1_000_000).toLocaleString();
    } catch {
      return '—';
    }
  }
</script>

<main class="page">
  <div class="page-head">
    <h1>{collectionName || 'Registry Collection'}</h1>
    <div class="badge-row">
      <span class="badge badge-muted">ICRC-7</span>
      <span class="badge badge-muted">ICRC-37</span>
      {#if testMode}
        <span class="badge badge-warning">Test mode</span>
      {/if}
      {#if canMint}
        <span class="badge">Authorized minter</span>
      {/if}
    </div>
  </div>

  {#if collectionDescription}
    <p class="card-note">{collectionDescription}</p>
  {:else}
    <p class="card-note">
      Shared registry for tokenized assets — land parcels, licenses, certificates, or any
      other uniquely identifiable asset represented as an ICRC-7 NFT.
    </p>
  {/if}

  {#if loading}
    <div class="loading">Loading registry…</div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else}
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Symbol</div>
        <div class="stat-value">{collectionSymbol || '—'}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total supply</div>
        <div class="stat-value">{totalSupply}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Supply cap</div>
        <div class="stat-value">{supplyCap ?? '∞'}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Displayed</div>
        <div class="stat-value">{tokens.length}</div>
      </div>
    </div>

    <div class="layout-grid">
      <div>
        <div class="card">
          <h2>Registered assets</h2>
          {#if tokens.length === 0}
            <div class="no-data">No assets registered yet.</div>
          {:else}
            <div class="nft-grid">
              {#each tokens as token}
                <a
                  class="nft-card"
                  class:frozen={token.frozen}
                  href="/t/{token.id}"
                >
                  <div class="nft-visual">
                    {#if token.geo?.h3Indexes?.length || (token.geo?.lat != null && token.geo?.lng != null)}
                      <AssetGeoMap geo={token.geo} compact={true} />
                    {:else}
                      ◆
                    {/if}
                  </div>
                  <div class="nft-body">
                    <div class="nft-title">{tokenDisplayName(token)}</div>
                    <div class="nft-subtitle">{tokenSubtitle(token)}</div>
                    <div class="nft-owner">Owner {truncate(token.owner)}</div>
                    <div class="nft-badges">
                      {#if token.frozen}
                        <span class="badge badge-danger">Frozen</span>
                      {/if}
                      {#if token.owner === viewer}
                        <span class="badge badge-muted">Yours</span>
                      {/if}
                      {#if token.authority === viewer}
                        <span class="badge">Authority</span>
                      {/if}
                    </div>
                  </div>
                </a>
              {/each}
            </div>
          {/if}
        </div>

        <div class="card">
          <h2>Recent registry events</h2>
          {#if transactions.length === 0}
            <div class="no-data">No events recorded yet.</div>
          {:else}
            <table class="tx-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Kind</th>
                  <th>Asset</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {#each transactions as tx}
                  <tr>
                    <td>{tx.id}</td>
                    <td><span class="tx-kind">{tx.kind}</span></td>
                    <td>#{tx.tokenId}</td>
                    <td>{truncate(tx.from)}</td>
                    <td>{truncate(tx.to)}</td>
                    <td>{formatTime(tx.timestamp)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      </div>

      <aside>
        {#if !$isAuthenticated}
          <div class="card">
            <h2>Sign in required</h2>
            <p class="hint">
              Connect with Internet Identity to transfer assets or perform registry
              authority actions. Minting, forced transfer, freeze, and authority handover
              are restricted to authorized principals enforced on-chain.
            </p>
          </div>
        {:else if canMint}
          <div class="card">
            <h2>Mint asset</h2>
            <p class="hint">
              Your principal is an authorized minter. Token IDs are assigned sequentially
              by the registry.
            </p>
            <div class="form-grid">
              <div>
                <label for="mintOwner">Owner principal</label>
                <input
                  id="mintOwner"
                  bind:value={mintOwner}
                  placeholder={viewer}
                  disabled={minting}
                />
              </div>
              <div>
                <label for="mintName">Display name</label>
                <input id="mintName" bind:value={mintName} placeholder="Certificate #42" disabled={minting} />
              </div>
              <div>
                <label for="mintAssetType">Asset type</label>
                <input id="mintAssetType" bind:value={mintAssetType} placeholder="land, license, deed…" disabled={minting} />
              </div>
            </div>
            <div class="btn-row">
              <button class="btn btn-primary" disabled={minting} on:click={handleMint}>
                {minting ? 'Minting…' : 'Mint asset'}
              </button>
            </div>
          </div>
        {:else}
          <div class="card">
            <h2>Registry permissions</h2>
            <p class="hint">
              You can transfer assets you own. Minting and authority operations require an
              authorized minter principal configured on the registry canister.
            </p>
          </div>
        {/if}

        <div class="card">
          <h3>Authorized minters</h3>
          {#if authorizedMinters.length === 0}
            <p class="hint">No authorized minters configured.</p>
          {:else}
            <div class="detail-grid">
              {#each authorizedMinters as minter}
                <code>{minter}</code>
              {/each}
            </div>
          {/if}
        </div>
      </aside>
    </div>
  {/if}
</main>