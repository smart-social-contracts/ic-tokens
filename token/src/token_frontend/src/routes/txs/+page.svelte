<script>
  import "../../index.scss";
  import { backend } from "$lib/canisters";
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";

  let transactions = [];
  let loading = true;
  let error = null;
  let currentPage = 0;
  let pageSize = 20;
  let totalCount = 0;
  let hasMore = false;
  let decimals = 8;
  let tokenSymbol = "SMPL";

  $: currentPage = parseInt($page.url.searchParams.get("page") || "0");

  function formatAmount(amount, dec) {
    const value = Number(amount) / Math.pow(10, dec);
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }

  function formatTimestamp(nanos) {
    const ms = Number(nanos) / 1_000_000;
    return new Date(ms).toLocaleString();
  }

  function truncateAddress(address) {
    if (!address) return "—";
    if (address.length <= 20) return address;
    return `${address.slice(0, 10)}...${address.slice(-8)}`;
  }

  function getKindBadgeClass(kind) {
    switch (kind) {
      case "mint": return "badge-mint";
      case "burn": return "badge-burn";
      default: return "badge-transfer";
    }
  }

  async function loadTransactions() {
    loading = true;
    error = null;
    try {
      const [info, result] = await Promise.all([
        backend.get_token_info(),
        backend.get_transactions(BigInt(currentPage), BigInt(pageSize)),
      ]);
      decimals = Number(info.decimals);
      tokenSymbol = info.symbol;
      transactions = result.transactions;
      totalCount = Number(result.total_count);
      hasMore = result.has_more;
    } catch (e) {
      console.error("Error loading transactions:", e);
      error = e.message || "Failed to load transactions";
    } finally {
      loading = false;
    }
  }

  function goToPage(p) {
    goto(`/txs?page=${p}`);
  }

  onMount(() => {
    loadTransactions();
  });

  $: if (currentPage !== undefined) {
    loadTransactions();
  }
</script>

<main>
  <div class="explorer-container">
    <div class="explorer-header">
      <a href="/" class="back-link">← Dashboard</a>
      <h1>📋 Transaction Explorer</h1>
      <p class="subtitle">Browse all token transactions</p>
    </div>

    {#if loading}
      <div class="loading">Loading transactions...</div>
    {:else if error}
      <div class="error">{error}</div>
    {:else}
      <div class="stats-bar">
        <span>Total: {totalCount} transactions</span>
        <span>Page {currentPage + 1} of {Math.ceil(totalCount / pageSize) || 1}</span>
      </div>

      <div class="table-container">
        <table class="tx-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>From</th>
              <th>To</th>
              <th>Amount</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {#each transactions as tx}
              <tr on:click={() => goto(`/tx/${tx.id}`)} class="clickable">
                <td class="tx-id">#{tx.id.toString()}</td>
                <td><span class="badge {getKindBadgeClass(tx.kind)}">{tx.kind}</span></td>
                <td class="address" title={tx.from_address}>{truncateAddress(tx.from_address)}</td>
                <td class="address" title={tx.to_address}>{truncateAddress(tx.to_address)}</td>
                <td class="amount">{formatAmount(tx.amount, decimals)} {tokenSymbol}</td>
                <td class="time">{formatTimestamp(tx.timestamp)}</td>
              </tr>
            {:else}
              <tr>
                <td colspan="6" class="no-data">No transactions yet</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <button disabled={currentPage === 0} on:click={() => goToPage(0)}>First</button>
        <button disabled={currentPage === 0} on:click={() => goToPage(currentPage - 1)}>Previous</button>
        <span class="page-info">Page {currentPage + 1}</span>
        <button disabled={!hasMore} on:click={() => goToPage(currentPage + 1)}>Next</button>
      </div>
    {/if}
  </div>
</main>

<style>
  .explorer-container {
    max-width: 1000px;
    width: 100%;
    margin: 0 auto;
  }

  .explorer-header {
    margin-bottom: 24px;
  }

  .back-link {
    color: var(--color-text-tertiary);
    text-decoration: none;
    font-size: 0.875rem;
    display: inline-block;
    margin-bottom: 8px;
  }

  .back-link:hover {
    color: var(--color-text-primary);
  }

  .explorer-header h1 {
    margin: 0 0 8px 0;
    font-size: 1.5rem;
  }

  .subtitle {
    color: var(--color-text-tertiary);
    margin: 0;
  }

  .stats-bar {
    display: flex;
    justify-content: space-between;
    padding: 12px 16px;
    background: var(--color-bg-tertiary);
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 0.875rem;
    color: var(--color-text-secondary);
  }

  .table-container {
    background: var(--color-bg-primary);
    border-radius: 12px;
    border: 1px solid var(--color-border);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
  }

  .tx-table {
    width: 100%;
    border-collapse: collapse;
  }

  .tx-table th {
    text-align: left;
    padding: 14px 16px;
    background: var(--color-bg-tertiary);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--color-text-tertiary);
    border-bottom: 1px solid var(--color-border);
  }

  .tx-table td {
    padding: 14px 16px;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.875rem;
  }

  .tx-table tr.clickable {
    cursor: pointer;
    transition: background 0.15s;
  }

  .tx-table tr.clickable:hover {
    background: var(--color-bg-tertiary);
  }

  .tx-id {
    font-family: monospace;
    color: var(--color-primary);
  }

  .address {
    font-family: monospace;
    font-size: 0.8rem;
  }

  .amount {
    font-weight: 600;
    color: var(--color-success);
  }

  .time {
    color: var(--color-text-tertiary);
    font-size: 0.8rem;
  }

  .badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .badge-transfer {
    background: #e5e5e5;
    color: #525252;
  }

  .badge-mint {
    background: #dcfce7;
    color: #166534;
  }

  .badge-burn {
    background: #fef2f2;
    color: #dc2626;
  }

  .no-data {
    text-align: center;
    color: var(--color-text-tertiary);
    padding: 32px !important;
  }

  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    margin-top: 20px;
  }

  .pagination button {
    padding: 8px 16px;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    background: var(--color-bg-primary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.15s;
  }

  .pagination button:hover:not(:disabled) {
    background: var(--color-bg-tertiary);
    border-color: var(--color-border-hover);
  }

  .pagination button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-info {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
  }

  .loading, .error {
    text-align: center;
    padding: 48px;
    background: var(--color-bg-primary);
    border-radius: 12px;
    border: 1px solid var(--color-border);
  }

  .error {
    color: var(--color-error);
    background: #fef2f2;
    border-color: #fecaca;
  }
</style>
