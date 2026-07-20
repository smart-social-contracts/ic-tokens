<script>
  import { login, logout } from '$lib/auth.js';
  import { isAuthenticated, principal } from '$lib/stores/auth.js';
  import { truncate } from '$lib/metadata.js';

  let busy = false;
  let error = '';

  async function handleLogin() {
    busy = true;
    error = '';
    try {
      await login();
    } catch (e) {
      error = e?.message || 'Login failed';
    } finally {
      busy = false;
    }
  }

  async function handleLogout() {
    busy = true;
    error = '';
    try {
      await logout();
    } catch (e) {
      error = e?.message || 'Logout failed';
    } finally {
      busy = false;
    }
  }
</script>

<div class="auth-shell">
  {#if $isAuthenticated}
    <div class="auth-user">
      <span class="auth-label">Signed in</span>
      <code class="auth-principal">{truncate($principal, 10, 8)}</code>
    </div>
    <button class="btn btn-secondary" disabled={busy} on:click={handleLogout}>
      {busy ? 'Signing out…' : 'Sign out'}
    </button>
  {:else}
    <button class="btn btn-primary" disabled={busy} on:click={handleLogin}>
      {busy ? 'Connecting…' : 'Sign in with Internet Identity'}
    </button>
  {/if}
  {#if error}
    <p class="auth-error">{error}</p>
  {/if}
</div>

<style>
  .auth-shell {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .auth-user {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }

  .auth-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-tertiary);
  }

  .auth-principal {
    font-size: 0.82rem;
    color: var(--color-text-secondary);
    background: var(--color-bg-tertiary);
    padding: 4px 8px;
    border-radius: 6px;
  }

  .auth-error {
    width: 100%;
    margin: 0;
    color: var(--color-error-700);
    font-size: 0.85rem;
  }
</style>
