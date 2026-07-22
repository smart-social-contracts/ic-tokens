<script>
  import { onMount } from 'svelte';
  import '../index.scss';
  import AuthButton from '$lib/components/AuthButton.svelte';
  import { restoreAuthSession } from '$lib/auth.js';
  import { initBackendWithIdentity, backendReady } from '$lib/canisters.js';

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
      <div class="brand-mark">R</div>
    </div>
    <AuthButton />
  </header>

  {#if booting || !$backendReady}
    <div class="boot-state">Connecting to registry…</div>
  {:else}
    <slot />
  {/if}

  <footer class="app-footer">
    <a href={repoUrl} target="_blank" rel="noopener noreferrer" class="footer-link">ic-tokens</a>
    <div class="footer-meta">v{version} ({commitHash})</div>
  </footer>
</div>
