<script>
  import "../../../index.scss";
  import { backend } from "$lib/canisters";
  import { onMount } from "svelte";
  import { page } from "$app/stores";

  let transaction = null;
  let loading = true;
  let error = null;
  let decimals = 8;
  let tokenSymbol = "SMPL";
  let copiedField = null;

  $: txId = $page.params.id;

  function formatAmount(amount, dec) {
    const value = Number(amount) / Math.pow(10, dec);
    return value.toLocaleString(undefined, { maximumFractionDigits: 8 });
  }

  function formatTimestamp(nanos) {
    const ms = Number(nanos) / 1_000_000;
    const date = new Date(ms);
    return date.toISOString();
  }

  function getKindBadgeClass(kind) {
    switch (kind) {
      case "mint": return "badge-mint";
      case "burn": return "badge-burn";
      default: return "badge-transfer";
    }
  }

  async function copyToClipboard(text, field) {
    try {
      await navigator.clipboard.writeText(text);
      copiedField = field;
      setTimeout(() => copiedField = null, 1500);
    } catch (e) {
      console.error("Copy failed:", e);
    }
  }

  async function loadTransaction() {
    loading = true;
    error = null;
    try {
      const [info, tx] = await Promise.all([
        backend.get_token_info(),
        backend.get_transaction(BigInt(txId)),
      ]);
      decimals = Number(info.decimals);
      tokenSymbol = info.symbol;
      
      if (tx && tx.length > 0) {
        transaction = tx[0];
      } else {
        error = "Transaction not found";
      }
    } catch (e) {
      console.error("Error loading transaction:", e);
      error = e.message || "Failed to load transaction";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadTransaction();
  });
</script>

<main>
  <div class="detail-container">
    <div class="detail-header">
      <a href="/txs" class="back-link">← Back to Transactions</a>
      <h1>📄 Transaction Details</h1>
    </div>

    {#if loading}
      <div class="loading">Loading transaction...</div>
    {:else if error}
      <div class="error">{error}</div>
    {:else if transaction}
      <div class="detail-card">
        <div class="detail-row header-row">
          <span class="label">Transaction ID</span>
          <span class="value tx-id">
            #{transaction.id.toString()}
            <button class="copy-btn" on:click={() => copyToClipboard(transaction.id.toString(), 'txid')}>
              {copiedField === 'txid' ? '✓' : '📋'}
            </button>
          </span>
        </div>

        <div class="detail-row">
          <span class="label">Type</span>
          <span class="value">
            <span class="badge {getKindBadgeClass(transaction.kind)}">{transaction.kind}</span>
          </span>
        </div>

        <div class="detail-row">
          <span class="label">Amount</span>
          <span class="value amount">{formatAmount(transaction.amount, decimals)} {tokenSymbol}</span>
        </div>

        {#if transaction.fee > 0}
          <div class="detail-row">
            <span class="label">Fee</span>
            <span class="value fee">{formatAmount(transaction.fee, decimals)} {tokenSymbol}</span>
          </div>
        {/if}

        <div class="detail-row">
          <span class="label">Datetime</span>
          <span class="value mono">
            {formatTimestamp(transaction.timestamp)}
            <button class="copy-btn" on:click={() => copyToClipboard(formatTimestamp(transaction.timestamp), 'datetime')}>
              {copiedField === 'datetime' ? '✓' : '📋'}
            </button>
          </span>
        </div>

        <div class="section-divider"></div>

        <div class="detail-row">
          <span class="label">From</span>
          <span class="value address">
            {#if transaction.from_owner}
              {transaction.from_owner}
              {#if transaction.from_subaccount}
                <span class="subaccount">:{transaction.from_subaccount}</span>
              {/if}
              <button class="copy-btn" on:click={() => copyToClipboard(transaction.from_owner + (transaction.from_subaccount ? ':' + transaction.from_subaccount : ''), 'from')}>
                {copiedField === 'from' ? '✓' : '📋'}
              </button>
            {:else}
              <span class="minted">— (Minted)</span>
            {/if}
          </span>
        </div>

        <div class="detail-row">
          <span class="label">To</span>
          <span class="value address">
            {transaction.to_owner}
            {#if transaction.to_subaccount}
              <span class="subaccount">:{transaction.to_subaccount}</span>
            {/if}
            <button class="copy-btn" on:click={() => copyToClipboard(transaction.to_owner + (transaction.to_subaccount ? ':' + transaction.to_subaccount : ''), 'to')}>
              {copiedField === 'to' ? '✓' : '📋'}
            </button>
          </span>
        </div>

        {#if transaction.memo}
          <div class="section-divider"></div>
          <div class="detail-row">
            <span class="label">Memo</span>
            <span class="value memo">
              {transaction.memo}
              <button class="copy-btn" on:click={() => copyToClipboard(transaction.memo, 'memo')}>
                {copiedField === 'memo' ? '✓' : '📋'}
              </button>
            </span>
          </div>
        {/if}

        <div class="section-divider"></div>
        <div class="detail-row">
          <span class="label">Timestamp (ns)</span>
          <span class="value mono">
            {transaction.timestamp.toString()}
            <button class="copy-btn" on:click={() => copyToClipboard(transaction.timestamp.toString(), 'ts')}>
              {copiedField === 'ts' ? '✓' : '📋'}
            </button>
          </span>
        </div>
      </div>
    {/if}
  </div>
</main>

<style>
  .detail-container {
    max-width: 600px;
    width: 100%;
    margin: 0 auto;
  }

  .detail-header {
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

  .detail-header h1 {
    margin: 0;
    font-size: 1.5rem;
  }

  .detail-card {
    background: var(--color-bg-primary);
    border-radius: 12px;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-md);
    overflow: hidden;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 16px 20px;
    border-bottom: 1px solid var(--color-border);
  }

  .detail-row:last-child {
    border-bottom: none;
  }

  .header-row {
    background: var(--color-bg-tertiary);
  }

  .label {
    color: var(--color-text-tertiary);
    font-size: 0.875rem;
    font-weight: 500;
    flex-shrink: 0;
    margin-right: 16px;
  }

  .value {
    font-weight: 500;
    text-align: right;
    word-break: break-all;
  }

  .tx-id {
    font-family: monospace;
    font-size: 1.25rem;
    color: var(--color-primary);
  }

  .amount {
    font-size: 1.1rem;
    color: var(--color-success);
    font-weight: 600;
  }

  .fee {
    color: var(--color-text-tertiary);
  }

  .address {
    font-family: monospace;
    font-size: 0.8rem;
    max-width: 350px;
  }

  .subaccount {
    color: var(--color-text-tertiary);
  }

  .minted {
    color: var(--color-text-tertiary);
    font-style: italic;
  }

  .memo {
    font-family: monospace;
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .mono {
    font-family: monospace;
    font-size: 0.8rem;
    color: var(--color-text-tertiary);
  }

  .badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 0.75rem;
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

  .section-divider {
    height: 1px;
    background: var(--color-border);
    margin: 0;
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

  .copy-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px 6px;
    margin-left: 8px;
    font-size: 0.75rem;
    opacity: 0.5;
    transition: opacity 0.15s;
    vertical-align: middle;
  }

  .copy-btn:hover {
    opacity: 1;
  }
</style>
