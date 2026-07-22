<script>
  import AssetGeoMap from '$lib/components/AssetGeoMap.svelte';
  import { tokenDisplayName, tokenSubtitle, truncate } from '$lib/metadata.js';
  import { isAuthenticated, principal } from '$lib/stores/auth.js';

  export let token = null;

  $: viewer = $principal;
  $: isOwner = viewer && token.owner === viewer;
  $: isAuthority = viewer && token.authority === viewer;
  $: hasGeo =
    token?.geo?.h3Indexes?.length > 0 ||
    (token?.geo?.lat != null && token?.geo?.lng != null);
  $: geoReady = token?.geo && hasGeo;
</script>

<a class="nft-card" class:frozen={token.frozen} href="/t/{token.id}">
  <div class="nft-visual">
    {#if geoReady}
      <AssetGeoMap geo={token.geo} compact={true} />
    {:else}
      <span class="nft-fallback">◆</span>
    {/if}
  </div>
  <div class="nft-body">
    <div class="nft-title">
      {tokenDisplayName(token)}
      {#if token.frozen}
        <span class="badge badge-danger">Frozen</span>
      {/if}
    </div>
    <div class="nft-subtitle">{tokenSubtitle(token)}</div>
    <div class="nft-owner">{truncate(token.owner)}</div>
    <div class="nft-badges">
      {#if isOwner}
        <span class="badge badge-accent">Yours</span>
      {/if}
      {#if isAuthority}
        <span class="badge badge-accent">Authority</span>
      {/if}
    </div>
  </div>
</a>

<style>
  .nft-fallback {
    color: var(--text-tertiary);
  }
</style>
