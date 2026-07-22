<script>
  import "../index.scss";
  import { backend } from "$lib/canisters";
  import { login, logout, restoreAuthSession } from "$lib/auth.js";
  import { isAuthenticated, principal as authPrincipal } from "$lib/stores/auth.js";
  import { Principal } from "@dfinity/principal";
  import { onMount, onDestroy } from "svelte";
  import { Chart, PieController, ArcElement, Tooltip, Legend } from "chart.js";

  Chart.register(PieController, ArcElement, Tooltip, Legend);

  let tokenName = "Loading...";
  let tokenSymbol = "";
  let totalSupply = "Loading...";
  let decimals = 8;
  let fee = 0;
  let loading = true;
  let error = null;

  let testMode = false;
  let myPrincipal = "";
  let myBalance = null;
  let authBusy = false;
  let mintRecipient = "";
  let mintAmount = "";
  let minting = false;
  let mintResult = null;
  let mintError = null;

  let canManageToken = false;
  let editName = "";
  let editSymbol = "";
  let metadataSaving = false;
  let metadataResult = null;
  let metadataError = null;

  let transferFrom = "";
  let transferTo = "";
  let transferAmount = "";
  let fromBalance = null;
  let transferring = false;
  let transferResult = null;
  let transferError = null;

  let distributionLoading = true;
  let distributionError = null;
  let holderCount = 0;
  let topHolders = [];
  let chartCanvas;
  let chart = null;
  let chartData = [];

  let recentTxs = [];
  let txLoading = true;
  let totalTxCount = 0;
  let copiedAddr = null;

  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      copiedAddr = text;
      setTimeout(() => copiedAddr = null, 1500);
    } catch (e) {
      console.error("Copy failed:", e);
    }
  }

  const CHART_COLORS = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#ec4899", "#84cc16", "#6366f1", "#a3a3a3",
  ];

  function formatSupply(supply, dec) {
    const value = Number(supply) / Math.pow(10, dec);
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function formatAmount(amount, dec) {
    const value = Number(amount) / Math.pow(10, dec);
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }

  function parseAmount(amountStr, dec) {
    const value = parseFloat(amountStr);
    if (isNaN(value) || value <= 0) {
      return null;
    }
    return BigInt(Math.floor(value * Math.pow(10, dec)));
  }

  function truncateAddress(address) {
    if (!address) return "—";
    if (address.length <= 16) return address;
    return `${address.slice(0, 8)}...${address.slice(-6)}`;
  }

  function formatTimestamp(nanos) {
    const ms = Number(nanos) / 1_000_000;
    const date = new Date(ms);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return "just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  }

  async function refreshAccount() {
    myPrincipal = await backend.get_my_principal();
    myBalance = await backend.get_my_balance();
    if (!testMode || !transferFrom.trim()) {
      transferFrom = myPrincipal;
    }
  }

  async function refreshFromBalance() {
    const from = (testMode ? transferFrom : myPrincipal).trim();
    if (!from) {
      fromBalance = null;
      return;
    }
    try {
      const owner = Principal.fromText(from);
      fromBalance = await backend.icrc1_balance_of({
        owner,
        subaccount: [],
      });
    } catch (e) {
      fromBalance = null;
    }
  }

  async function refreshTokenInfo() {
    const info = await backend.get_token_info();
    totalSupply = formatSupply(info.total_supply, decimals);
  }

  async function loadDistribution() {
    distributionLoading = true;
    distributionError = null;

    try {
      const [distribution, holders] = await Promise.all([
        backend.get_token_distribution(),
        backend.get_top_holders(BigInt(10)),
      ]);
      
      holderCount = Number(distribution.holder_count);
      topHolders = holders;
      const total = Number(distribution.total_supply);

      if (distribution.holders.length === 0) {
        distributionLoading = false;
        return;
      }

      const TOP_N = 6;
      const allHolders = distribution.holders;
      chartData = [];
      let othersBalance = 0n;

      for (let i = 0; i < allHolders.length; i++) {
        if (i < TOP_N) {
          chartData.push({
            address: allHolders[i].address,
            balance: Number(allHolders[i].balance),
            percentage: (Number(allHolders[i].balance) / total) * 100,
          });
        } else {
          othersBalance += BigInt(allHolders[i].balance);
        }
      }

      if (othersBalance > 0n) {
        chartData.push({
          address: `Others (${allHolders.length - TOP_N})`,
          balance: Number(othersBalance),
          percentage: (Number(othersBalance) / total) * 100,
        });
      }

      if (chart) {
        chart.destroy();
        chart = null;
      }

      // Use requestAnimationFrame to ensure canvas is ready
      requestAnimationFrame(() => {
        if (chartCanvas && chartData.length > 0) {
          const ctx = chartCanvas.getContext('2d');
          chart = new Chart(ctx, {
            type: "pie",
            data: {
              labels: chartData.map((d) => truncateAddress(d.address)),
              datasets: [
                {
                  data: chartData.map((d) => d.balance),
                  backgroundColor: CHART_COLORS.slice(0, chartData.length),
                  borderColor: "#FFFFFF",
                  borderWidth: 2,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: true,
              plugins: {
                legend: {
                  display: false,
                },
                tooltip: {
                  callbacks: {
                    label: (context) => {
                      const item = chartData[context.dataIndex];
                      const formattedBalance = formatSupply(item.balance, decimals);
                      return `${formattedBalance} ${tokenSymbol} (${item.percentage.toFixed(1)}%)`;
                    },
                    title: (context) => {
                      return chartData[context[0].dataIndex].address;
                    },
                  },
                },
              },
            },
          });
        }
      });

      distributionLoading = false;
    } catch (e) {
      console.error("Error loading distribution:", e);
      distributionError = e.message || "Failed to load distribution";
      distributionLoading = false;
    }
  }

  async function loadRecentTransactions() {
    txLoading = true;
    try {
      const result = await backend.get_transactions(BigInt(0), BigInt(5));
      recentTxs = result.transactions;
      totalTxCount = Number(result.total_count);
    } catch (e) {
      console.error("Error loading transactions:", e);
    } finally {
      txLoading = false;
    }
  }

  async function handleSaveMetadata() {
    metadataResult = null;
    metadataError = null;

    const name = editName.trim();
    const symbol = editSymbol.trim().toUpperCase();
    if (!name || !symbol) {
      metadataError = "Name and symbol are required";
      return;
    }

    metadataSaving = true;
    try {
      const result = await backend.update_token_metadata({ name, symbol });
      if (result.success) {
        tokenName = result.name;
        tokenSymbol = result.symbol;
        editName = result.name;
        editSymbol = result.symbol;
        metadataResult = `Updated to ${result.name} (${result.symbol})`;
      } else {
        metadataError = result.error?.[0] || "Update failed";
      }
    } catch (e) {
      console.error("Metadata update error:", e);
      metadataError = e.message || "Failed to update token metadata";
    } finally {
      metadataSaving = false;
    }
  }

  async function handleMint() {
    mintResult = null;
    mintError = null;

    const recipient = mintRecipient.trim() || myPrincipal;
    const amount = parseAmount(mintAmount, decimals);

    if (!amount) {
      mintError = "Please enter a valid amount greater than 0";
      return;
    }

    let recipientPrincipal;
    try {
      recipientPrincipal = Principal.fromText(recipient);
    } catch (e) {
      mintError = "Invalid recipient principal address";
      return;
    }

    minting = true;
    try {
      const result = await backend.mint({
        to: { owner: recipientPrincipal, subaccount: [] },
        amount: amount,
      });

      if (result.success) {
        mintResult = `Minted ${mintAmount} ${tokenSymbol}`;
        mintAmount = "";
        await refreshAccount();
        await refreshTokenInfo();
        await loadDistribution();
        await loadRecentTransactions();
      } else {
        mintError = result.error?.[0] || "Mint operation failed";
      }
    } catch (e) {
      console.error("Mint error:", e);
      mintError = e.message || "Failed to mint tokens";
    } finally {
      minting = false;
    }
  }

  async function handleLogin() {
    authBusy = true;
    transferError = null;
    try {
      await login();
      await refreshAccount();
    } catch (e) {
      console.error("Login error:", e);
      transferError = e.message || "Failed to sign in";
    } finally {
      authBusy = false;
    }
  }

  async function handleLogout() {
    authBusy = true;
    try {
      await logout();
      await refreshAccount();
    } catch (e) {
      console.error("Logout error:", e);
    } finally {
      authBusy = false;
    }
  }

  async function handleTransfer() {
    transferResult = null;
    transferError = null;

    const sender = (testMode ? transferFrom : myPrincipal).trim();
    const recipient = transferTo.trim();
    const amount = parseAmount(transferAmount, decimals);

    if (!sender) {
      transferError = testMode ? "Enter a sender principal" : "Sign in to transfer tokens";
      return;
    }
    if (!recipient) {
      transferError = "Enter a recipient principal";
      return;
    }
    if (!amount) {
      transferError = "Please enter a valid amount greater than 0";
      return;
    }

    let recipientPrincipal;
    try {
      recipientPrincipal = Principal.fromText(recipient);
    } catch (e) {
      transferError = "Invalid recipient principal address";
      return;
    }

    if (testMode) {
      try {
        Principal.fromText(sender);
      } catch (e) {
        transferError = "Invalid sender principal address";
        return;
      }
    }

    if (recipient === sender) {
      transferError = "Sender and recipient must differ";
      return;
    }

    const totalCost = amount + BigInt(fee);
    const senderBalance = testMode ? fromBalance : myBalance;
    if (senderBalance !== null && senderBalance < totalCost) {
      transferError = `Insufficient balance (need ${formatAmount(totalCost, decimals)} ${tokenSymbol} including fee)`;
      return;
    }

    transferring = true;
    try {
      let result;
      if (testMode) {
        result = await backend.test_transfer({
          from_owner: sender,
          to: { owner: recipientPrincipal, subaccount: [] },
          amount,
        });
      } else {
        result = await backend.icrc1_transfer({
          to: { owner: recipientPrincipal, subaccount: [] },
          amount,
          fee: [],
          memo: [],
          from_subaccount: [],
          created_at_time: [],
        });
      }

      if (result.success) {
        const block = result.block_index?.[0];
        transferResult = block
          ? `Sent ${transferAmount} ${tokenSymbol} from ${truncateAddress(sender)} to ${truncateAddress(recipient)} (tx #${block})`
          : `Sent ${transferAmount} ${tokenSymbol} from ${truncateAddress(sender)} to ${truncateAddress(recipient)}`;
        transferAmount = "";
        await refreshAccount();
        await refreshFromBalance();
        await refreshTokenInfo();
        await loadDistribution();
        await loadRecentTransactions();
      } else {
        transferError = result.error?.[0] || "Transfer failed";
      }
    } catch (e) {
      console.error("Transfer error:", e);
      transferError = e.message || "Failed to transfer tokens";
    } finally {
      transferring = false;
    }
  }

  onMount(async () => {
    try {
      await restoreAuthSession();

      const [info, isTestMode] = await Promise.all([
        backend.get_token_info(),
        backend.is_test_mode(),
      ]);
      let manageToken = false;
      try {
        manageToken = await backend.can_manage_token();
      } catch (e) {
        console.warn("can_manage_token unavailable — upgrade token backend to enable renaming", e);
      }
      tokenName = info.name;
      tokenSymbol = info.symbol;
      editName = info.name;
      editSymbol = info.symbol;
      decimals = Number(info.decimals);
      fee = Number(info.fee);
      totalSupply = formatSupply(info.total_supply, decimals);
      testMode = isTestMode;
      canManageToken = manageToken || isTestMode;
      await refreshAccount();
      if (testMode) {
        transferFrom = myPrincipal;
        await refreshFromBalance();
      }
      loading = false;

      await Promise.all([
        loadDistribution(),
        loadRecentTransactions(),
      ]);
    } catch (e) {
      console.error("Error fetching token info:", e);
      error = e.message || "Failed to load token info";
      loading = false;
    }
  });

  onDestroy(() => {
    if (chart) {
      chart.destroy();
    }
  });
</script>

<main>
  <div class="dashboard">
    <header class="dashboard-header">
      <h1>🪙 {tokenName || "Token"} Dashboard</h1>
      {#if tokenSymbol}
        <span class="badge">{tokenSymbol}</span>
      {/if}
    </header>

    {#if loading}
      <div class="loading-container">
        <div class="loading">Loading dashboard...</div>
      </div>
    {:else if error}
      <div class="error">{error}</div>
    {:else}
      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Supply</div>
          <div class="stat-value supply">{totalSupply}</div>
          <div class="stat-unit">{tokenSymbol}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Holders</div>
          <div class="stat-value">{holderCount}</div>
          <div class="stat-unit">addresses</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Transactions</div>
          <div class="stat-value">{totalTxCount}</div>
          <div class="stat-unit">total</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Transfer Fee</div>
          <div class="stat-value">{formatAmount(fee, decimals)}</div>
          <div class="stat-unit">{tokenSymbol}</div>
        </div>
      </div>

      <!-- Token identity (owner / authority / test mode) -->
      {#if canManageToken}
        <div class="card mint-card">
          <h2>🏷️ Token identity</h2>
          <p class="section-hint">
            Update the display name and ticker shown across this dashboard and ICRC-1 metadata.
          </p>
          <div class="mint-form">
            <div class="form-row">
              <div class="form-group">
                <label for="token-name">Name</label>
                <input
                  type="text"
                  id="token-name"
                  bind:value={editName}
                  placeholder="REALMS Token"
                  maxlength="64"
                  disabled={metadataSaving}
                />
              </div>
              <div class="form-group amount-group">
                <label for="token-symbol">Symbol</label>
                <input
                  type="text"
                  id="token-symbol"
                  bind:value={editSymbol}
                  placeholder="REALMS"
                  maxlength="16"
                  disabled={metadataSaving}
                />
              </div>
              <button class="mint-button" on:click={handleSaveMetadata} disabled={metadataSaving}>
                {metadataSaving ? "..." : "Save"}
              </button>
            </div>
            {#if metadataResult}
              <div class="mint-success">{metadataResult}</div>
            {/if}
            {#if metadataError}
              <div class="mint-error">{metadataError}</div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Transfer tokens -->
      <div class="card mint-card transfer-card">
        <h2>💸 Transfer Tokens</h2>
        <p class="section-hint">
          {#if testMode}
            Test mode: transfer from any sender principal to any recipient without signing in.
          {:else}
            Send {tokenSymbol} from your connected identity to another principal.
          {/if}
          Transfer fee: {formatAmount(fee, decimals)} {tokenSymbol}.
        </p>
        {#if testMode && fromBalance !== null}
          <p class="balance-hint">
            Sender balance: <strong>{formatAmount(fromBalance, decimals)} {tokenSymbol}</strong>
          </p>
        {:else if !testMode && myBalance !== null}
          <p class="balance-hint">
            Your balance: <strong>{formatAmount(myBalance, decimals)} {tokenSymbol}</strong>
          </p>
        {/if}

        {#if !testMode}
          <div class="auth-row">
            {#if $isAuthenticated}
              <span class="auth-status">Signed in as {truncateAddress($authPrincipal)}</span>
              <button type="button" class="auth-button secondary" on:click={handleLogout} disabled={authBusy}>
                Sign out
              </button>
            {:else}
              <span class="auth-status">Sign in with Internet Identity to send as your principal</span>
              <button type="button" class="auth-button" on:click={handleLogin} disabled={authBusy}>
                {authBusy ? "..." : "Sign in"}
              </button>
            {/if}
          </div>
        {/if}

        <div class="mint-form">
          <div class="form-row transfer-row">
            <div class="form-group">
              <label for="transfer-from">From (sender)</label>
              <input
                type="text"
                id="transfer-from"
                bind:value={transferFrom}
                readonly={!testMode}
                placeholder={testMode ? "Sender principal" : myPrincipal}
                title={testMode ? transferFrom : myPrincipal}
                disabled={transferring}
                on:change={refreshFromBalance}
                on:blur={refreshFromBalance}
              />
            </div>
            <div class="form-group">
              <label for="transfer-to">To (recipient)</label>
              <input
                type="text"
                id="transfer-to"
                bind:value={transferTo}
                placeholder="Recipient principal"
                disabled={transferring}
              />
            </div>
            <div class="form-group amount-group">
              <label for="transfer-amount">Amount</label>
              <input
                type="number"
                id="transfer-amount"
                bind:value={transferAmount}
                placeholder="0.00"
                min="0"
                step="any"
                disabled={transferring}
              />
            </div>
            <button class="mint-button" on:click={handleTransfer} disabled={transferring}>
              {transferring ? "..." : "Transfer"}
            </button>
          </div>
          {#if transferResult}
            <div class="mint-success">{transferResult}</div>
          {/if}
          {#if transferError}
            <div class="mint-error">{transferError}</div>
          {/if}
        </div>
      </div>

      <div class="main-grid">
        <!-- Distribution Section -->
        <div class="card distribution-card">
          <h2>📊 Distribution</h2>
          {#if distributionLoading}
            <div class="loading">Loading...</div>
          {:else if distributionError}
            <div class="error">{distributionError}</div>
          {:else if holderCount === 0}
            <div class="no-data">No token holders yet</div>
          {:else}
            <div class="chart-wrapper">
              <canvas bind:this={chartCanvas}></canvas>
            </div>
            <div class="chart-legend">
              {#each chartData as item, i}
                <div class="legend-item">
                  <span class="legend-color" style="background: {CHART_COLORS[i]}"></span>
                  <span class="legend-label" title={item.address}>{truncateAddress(item.address)}</span>
                  <span class="legend-value">{item.percentage.toFixed(1)}%</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Top Holders Section -->
        <div class="card holders-card">
          <h2>🏆 Top Holders</h2>
          {#if distributionLoading}
            <div class="loading">Loading...</div>
          {:else if topHolders.length === 0}
            <div class="no-data">No holders yet</div>
          {:else}
            <table class="holders-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Address</th>
                  <th>Balance</th>
                </tr>
              </thead>
              <tbody>
                {#each topHolders.slice(0, 10) as holder, i}
                  <tr>
                    <td class="rank">{i + 1}</td>
                    <td class="address" title={holder.address}>
                      {truncateAddress(holder.address)}
                      <button class="copy-btn" on:click|stopPropagation={() => copyToClipboard(holder.address)}>
                        {copiedAddr === holder.address ? '✓' : '📋'}
                      </button>
                    </td>
                    <td class="balance">{formatAmount(holder.balance, decimals)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      </div>

      <!-- Recent Transactions -->
      <div class="card transactions-card">
        <div class="card-header">
          <h2>📋 Recent Transactions</h2>
          <a href="/txs" class="view-all">View All →</a>
        </div>
        {#if txLoading}
          <div class="loading">Loading...</div>
        {:else if recentTxs.length === 0}
          <div class="no-data">No transactions yet</div>
        {:else}
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
              {#each recentTxs as tx}
                <tr class="clickable" on:click={() => window.location.href = `/tx/${tx.id}`}>
                  <td class="tx-id">#{tx.id.toString()}</td>
                  <td><span class="tx-badge {tx.kind}">{tx.kind}</span></td>
                  <td class="address" title={tx.from_address}>{truncateAddress(tx.from_address)}</td>
                  <td class="address" title={tx.to_address}>{truncateAddress(tx.to_address)}</td>
                  <td class="amount">{formatAmount(tx.amount, decimals)}</td>
                  <td class="time">{formatTimestamp(tx.timestamp)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <!-- Mint Section (Test Mode Only) -->
      {#if testMode}
        <div class="card mint-card">
          <h2>🧪 Mint Tokens (Test Mode)</h2>
          <div class="mint-form">
            <div class="form-row">
              <div class="form-group">
                <label for="recipient">Recipient</label>
                <input
                  type="text"
                  id="recipient"
                  bind:value={mintRecipient}
                  placeholder={truncateAddress(myPrincipal)}
                  disabled={minting}
                />
              </div>
              <div class="form-group amount-group">
                <label for="amount">Amount</label>
                <input
                  type="number"
                  id="amount"
                  bind:value={mintAmount}
                  placeholder="0.00"
                  min="0"
                  step="any"
                  disabled={minting}
                />
              </div>
              <button class="mint-button" on:click={handleMint} disabled={minting}>
                {minting ? "..." : "Mint"}
              </button>
            </div>
            {#if mintResult}
              <div class="mint-success">{mintResult}</div>
            {/if}
            {#if mintError}
              <div class="mint-error">{mintError}</div>
            {/if}
          </div>
        </div>
      {/if}
    {/if}
  </div>
</main>
