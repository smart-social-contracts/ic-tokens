<script>
  import { onMount } from 'svelte';
  import { Principal } from '@dfinity/principal';
  import { backend } from '$lib/canisters';

  let loading = true;
  let error = null;
  
  // Collection info
  let collectionName = '';
  let collectionSymbol = '';
  let totalSupply = 0;
  let supplyCap = null;
  let testMode = false;
  
  // NFTs
  let tokens = [];
  let selectedToken = null;
  
  // Transactions
  let transactions = [];
  
  // Mint form
  let mintTokenId = '';
  let mintOwner = '';
  let mintName = '';
  let minting = false;
  let mintSuccess = null;
  let mintError = null;

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      loading = true;
      error = null;
      
      // Load collection info
      const [name, symbol, supply, cap, test] = await Promise.all([
        backend.icrc7_name(),
        backend.icrc7_symbol(),
        backend.icrc7_total_supply(),
        backend.icrc7_supply_cap(),
        backend.is_test_mode().catch(() => false)
      ]);
      
      collectionName = name;
      collectionSymbol = symbol;
      totalSupply = Number(supply);
      supplyCap = cap && cap.length > 0 ? Number(cap[0]) : null;
      testMode = test;
      
      // Load tokens
      const tokenIds = await backend.icrc7_tokens([], []);
      tokens = await Promise.all(
        tokenIds.slice(0, 20).map(async (id) => {
          const owner = await backend.icrc7_owner_of(id);
          const metadata = await backend.icrc7_token_metadata(id).catch(() => []);
          return {
            id: Number(id),
            owner: owner && owner.length > 0 ? owner[0].owner.toText() : 'Unknown',
            metadata: metadata
          };
        })
      );
      
      // Load transactions
      const txs = await backend.get_transactions(0n, 10n);
      transactions = txs.map(tx => ({
        id: Number(tx.id),
        kind: tx.kind,
        tokenId: Number(tx.token_id),
        from: tx.from_principal || '-',
        to: tx.to_principal || '-',
        timestamp: tx.timestamp
      }));
      
    } catch (e) {
      console.error('Failed to load data:', e);
      error = e.message || 'Failed to load data';
    } finally {
      loading = false;
    }
  }

  async function handleMint() {
    if (!mintTokenId || !mintOwner) return;
    
    try {
      minting = true;
      mintSuccess = null;
      mintError = null;
      
      const metadata = mintName 
        ? [[['name', { Text: mintName }]]]
        : [];
      
      const result = await backend.mint({
        token_id: BigInt(mintTokenId),
        owner: {
          owner: Principal.fromText(mintOwner),
          subaccount: []
        },
        metadata: metadata.length > 0 ? [metadata[0]] : []
      });
      
      if ('Ok' in result) {
        mintSuccess = `NFT #${mintTokenId} minted successfully!`;
        mintTokenId = '';
        mintOwner = '';
        mintName = '';
        await loadData();
      } else {
        mintError = result.Err?.message || 'Mint failed';
      }
    } catch (e) {
      console.error('Mint failed:', e);
      mintError = e.message || 'Mint failed';
    } finally {
      minting = false;
    }
  }

  function truncateAddress(addr) {
    if (!addr || addr.length <= 16) return addr;
    return addr.slice(0, 8) + '...' + addr.slice(-6);
  }

  function getTokenName(token) {
    if (!token.metadata || token.metadata.length === 0) return `NFT #${token.id}`;
    const nameMeta = token.metadata.find(m => m[0] === 'name');
    if (nameMeta && nameMeta[1] && 'Text' in nameMeta[1]) {
      return nameMeta[1].Text;
    }
    return `NFT #${token.id}`;
  }

  function formatTime(timestamp) {
    if (!timestamp) return '-';
    try {
      const date = new Date(Number(timestamp) / 1_000_000);
      return date.toLocaleString();
    } catch {
      return '-';
    }
  }
</script>

<main>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>{collectionName || 'NFT Collection'}</h1>
      <span class="badge">ICRC-7</span>
      <span class="badge">ICRC-37</span>
      {#if testMode}
        <span class="badge test">TEST MODE</span>
      {/if}
    </div>

    {#if loading}
      <div class="loading">Loading collection data...</div>
    {:else if error}
      <div class="error">{error}</div>
    {:else}
      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Collection</div>
          <div class="stat-value">{collectionSymbol}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Supply</div>
          <div class="stat-value supply">{totalSupply}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Supply Cap</div>
          <div class="stat-value">{supplyCap !== null ? supplyCap : '∞'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Displayed</div>
          <div class="stat-value">{tokens.length}</div>
        </div>
      </div>

      <!-- Mint Card (Test Mode Only) -->
      {#if testMode}
        <div class="card">
          <h2>🎨 Mint New NFT</h2>
          <div class="mint-form">
            <div class="form-row">
              <div class="form-group">
                <label for="tokenId">Token ID</label>
                <input 
                  id="tokenId"
                  type="number" 
                  bind:value={mintTokenId}
                  placeholder="1"
                  disabled={minting}
                />
              </div>
              <div class="form-group">
                <label for="owner">Owner Principal</label>
                <input 
                  id="owner"
                  type="text" 
                  bind:value={mintOwner}
                  placeholder="aaaaa-aa"
                  disabled={minting}
                />
              </div>
              <div class="form-group">
                <label for="name">Name (optional)</label>
                <input 
                  id="name"
                  type="text" 
                  bind:value={mintName}
                  placeholder="My NFT"
                  disabled={minting}
                />
              </div>
            </div>
            <button 
              class="mint-button" 
              on:click={handleMint}
              disabled={minting || !mintTokenId || !mintOwner}
            >
              {minting ? 'Minting...' : 'Mint NFT'}
            </button>
            {#if mintSuccess}
              <div class="mint-success">{mintSuccess}</div>
            {/if}
            {#if mintError}
              <div class="mint-error">{mintError}</div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- NFT Grid -->
      <div class="card">
        <h2>🖼️ NFT Collection</h2>
        {#if tokens.length === 0}
          <div class="no-data">No NFTs minted yet</div>
        {:else}
          <div class="nft-grid">
            {#each tokens as token}
              <div class="nft-card" on:click={() => selectedToken = token}>
                <div class="nft-image">
                  🎨
                </div>
                <div class="nft-info">
                  <div class="nft-id">#{token.id}</div>
                  <div class="nft-name">{getTokenName(token)}</div>
                  <div class="nft-owner">{truncateAddress(token.owner)}</div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Recent Transactions -->
      <div class="card">
        <h2>📜 Recent Transactions</h2>
        {#if transactions.length === 0}
          <div class="no-data">No transactions yet</div>
        {:else}
          <table class="tx-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Token</th>
                <th>From</th>
                <th>To</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {#each transactions as tx}
                <tr>
                  <td>{tx.id}</td>
                  <td><span class="tx-badge {tx.kind}">{tx.kind}</span></td>
                  <td>#{tx.tokenId}</td>
                  <td class="address">{truncateAddress(tx.from)}</td>
                  <td class="address">{truncateAddress(tx.to)}</td>
                  <td>{formatTime(tx.timestamp)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    {/if}
  </div>
</main>

<!-- Token Detail Modal -->
{#if selectedToken}
  <div class="modal-overlay" on:click={() => selectedToken = null}>
    <div class="modal" on:click|stopPropagation>
      <div class="modal-header">
        <h2>NFT #{selectedToken.id}</h2>
        <button class="modal-close" on:click={() => selectedToken = null}>×</button>
      </div>
      <div class="nft-image" style="height: 200px; border-radius: 8px; margin-bottom: 20px;">
        🎨
      </div>
      <div class="detail-row">
        <span class="detail-label">Token ID</span>
        <span class="detail-value">{selectedToken.id}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Name</span>
        <span class="detail-value">{getTokenName(selectedToken)}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Owner</span>
        <span class="detail-value">{selectedToken.owner}</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .badge.test {
    background: #f59e0b;
  }
</style>
