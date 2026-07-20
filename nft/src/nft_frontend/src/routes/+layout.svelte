<script>
  import { onMount } from 'svelte';
  import '../index.scss';
  import AuthButton from '$lib/components/AuthButton.svelte';
  import { restoreAuthSession } from '$lib/auth.js';
  import { initBackendWithIdentity } from '$lib/canisters.js';
  import { backendReady } from '$lib/canisters.js';

  const version = __APP_VERSION__ || 'dev';
  const commitHash = __COMMIT_HASH__ || 'local';
  const repoUrl = 'https://github.com/smart-social-contracts/ic-tokens';

  let booting = true;

  onMount(async () => {
    try {
      await initBackendWithIdentity(null);
      await restoreAuthSession();
    } finally {
      booting = false;
    }
  });
</script>

<div class="app-shell">
  <header class="app-header">
    <div class="brand-block">
      <div class="brand-kicker">Realms Registry</div>
      <div class="brand-title">Asset Collection</div>
      <div class="brand-subtitle">ICRC-7 / ICRC-37 tokenized assets on the Internet Computer</div>
    </div>
    <AuthButton />
  </header>

  {#if booting || !$backendReady}
    <div class="boot-state">Connecting to registry…</div>
  {:else}
    <slot />
  {/if}

  <footer class="app-footer">
    <div class="footer-row ic-branding">
      <img src="/internet-computer-icp-logo.svg" alt="Internet Computer" width="22" height="22" />
      <span>Built on the Internet Computer</span>
    </div>
    <a href={repoUrl} target="_blank" rel="noopener noreferrer" class="footer-link">ic-tokens</a>
    <div class="footer-meta">v{version} ({commitHash})</div>
  </footer>
</div>
