<script>
  import { onMount } from 'svelte';
  import { Principal } from '@dfinity/principal';
  import { getBackend } from '$lib/canisters.js';
  import { isAuthenticated, principal } from '$lib/stores/auth.js';
  import {
    metaText,
    normalizeTokenMetadata,
    tokenDisplayName,
    truncate,
  } from '$lib/metadata.js';
  import {
    extractGeoFromMetadata,
    hasGeoMetadata,
    resolveTokenGeo,
  } from '$lib/geo.js';
  import { filterTokens, tokenAssetType, tokenRealm, uniqueFilterOptions } from '$lib/filters.js';
  import NftCard from '$lib/components/NftCard.svelte';

  let loading = true;
  let error = null;
  let actionError = '';
  let actionSuccess = '';

  let collectionName = '';
  let collectionSymbol = '';
  let totalSupply = 0;
  let supplyCap = null;
  let testMode = false;
  let authorizedMinters = [];

  let tokens = [];
  let visibleCount = 12;

  let search = '';
  let filterType = '';
  let filterRealm = '';
  let filterAuthority = '';
  let filterOwner = '';
  let showFrozen = false;
  let mineOnly = false;

  let mintOwner = '';
  let mintName = '';
  let mintAssetType = '';
  let minting = false;

  $: viewer = $principal;
  $: canMint = $isAuthenticated && authorizedMinters.includes(viewer);

  $: assetTypes = uniqueFilterOptions(tokens, tokenAssetType);
  $: realms = uniqueFilterOptions(tokens, tokenRealm);
  $: authorities = uniqueFilterOptions(tokens, (t) => t.authority);
  $: owners = uniqueFilterOptions(tokens, (t) => t.owner);

  $: filters = {
    search,
    type: filterType,
    realm: filterRealm,
    authority: filterAuthority,
    owner: filterOwner,
    frozen: showFrozen,
    mineOnly,
    viewer,
  };

  $: filtered = filterTokens(tokens, filters);
  $: visible = filtered.slice(0, visibleCount);
  $: hasMore = visibleCount < filtered.length;

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

  function resetFilters() {
    search = '';
    filterType = '';
    filterRealm = '';
    filterAuthority = '';
    filterOwner = '';
    showFrozen = false;
    mineOnly = false;
    visibleCount = 12;
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

      const [name, symbol, supply, cap, test, minters] = await Promise.all([
        actor.icrc7_name(),
        actor.icrc7_symbol(),
        actor.icrc7_total_supply(),
        actor.icrc7_supply_cap(),
        actor.is_test_mode().catch(() => false),
        actor.list_authorized_minters().catch(() => []),
      ]);

      collectionName = name;
      collectionSymbol = symbol;
      totalSupply = Number(supply);
      supplyCap = cap && cap.length > 0 ? Number(cap[0]) : null;
      testMode = !!test;
      authorizedMinters = minters || [];

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
            frozenReason: metaText(normalizeTokenMetadata(tokenMetadata), 'frozen_reason'),
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

  function loadMore() {
    visibleCount += 12;
  }
</script>

<main class="page">
  <div class="hero">
    <div>
      <h1>{collectionName || 'Registry'}</h1>
      <div class="hero-meta">
        {collectionSymbol || '—'} · {totalSupply} assets
        {#if supplyCap} / {supplyCap} cap{/if}
        {#if testMode} · Test mode{/if}
      </div>
    </div>
    <div class="stats-row">
      <div class="stat-pill">
        <span class="stat-value">{filtered.length}</span>
        <span class="stat-label">shown</span>
      </div>
      <div class="stat-pill">
        <span class="stat-value">{totalSupply}</span>
        <span class="stat-label">total</span>
      </div>
    </div>
  </div>

  {#if actionSuccess}
    <div class="success-box">{actionSuccess}</div>
  {/if}
  {#if actionError}
    <div class="error-box">{actionError}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading registry…</div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else}
    <div class="filter-bar">
      <input
        type="text"
        placeholder="Search assets…"
        bind:value={search}
      />

      {#if assetTypes.length}
        <select bind:value={filterType}>
          <option value="">All types</option>
          {#each assetTypes as type}
            <option value={type}>{type}</option>
          {/each}
        </select>
      {/if}

      {#if realms.length}
        <select bind:value={filterRealm}>
          <option value="">All realms</option>
          {#each realms as realm}
            <option value={realm}>{truncate(realm)}</option>
          {/each}
        </select>
      {/if}

      {#if authorities.length}
        <select bind:value={filterAuthority}>
          <option value="">All authorities</option>
          {#each authorities as authority}
            <option value={authority}>{truncate(authority)}</option>
          {/each}
        </select>
      {/if}

      {#if $isAuthenticated}
        <button
          class="filter-pill"
          class:active={mineOnly}
          on:click={() => (mineOnly = !mineOnly)}
        >
          Mine only
        </button>
      {/if}

      <button
        class="filter-pill"
        class:active={showFrozen}
        on:click={() => (showFrozen = !showFrozen)}
      >
        Frozen
      </button>

      <button class="filter-pill" on:click={resetFilters}>Reset</button>
    </div>

    {#if visible.length === 0}
      <div class="no-data">No assets match the current filters.</div>
    {:else}
      <div class="nft-grid">
        {#each visible as token (token.id)}
          <NftCard {token} />
        {/each}
      </div>
    {/if}

    {#if hasMore}
      <div class="load-more">
        <button class="btn btn-secondary" on:click={loadMore}>Load more</button>
      </div>
    {/if}

    {#if $isAuthenticated && canMint}
      <div class="card" style="margin-top: 32px;">
        <h2>Mint asset</h2>
        <div class="form-grid">
          <div>
            <label for="mintOwner">Owner</label>
            <input id="mintOwner" bind:value={mintOwner} placeholder={viewer} disabled={minting} />
          </div>
          <div>
            <label for="mintName">Name</label>
            <input id="mintName" bind:value={mintName} placeholder="Certificate #42" disabled={minting} />
          </div>
          <div>
            <label for="mintAssetType">Type</label>
            <input id="mintAssetType" bind:value={mintAssetType} placeholder="land, license, deed…" disabled={minting} />
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" disabled={minting} on:click={handleMint}>
            {minting ? 'Minting…' : 'Mint asset'}
          </button>
        </div>
      </div>
    {/if}
  {/if}
</main>

<style>
  .load-more {
    display: flex;
    justify-content: center;
    margin-top: 28px;
  }
</style>
