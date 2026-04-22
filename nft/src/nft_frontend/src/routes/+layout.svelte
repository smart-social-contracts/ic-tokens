<script>
  import "../index.scss";
  
  const version = __APP_VERSION__ || "dev";
  const commitHash = __COMMIT_HASH__ || "local";
  const buildTime = __BUILD_TIME__ || new Date().toISOString();
  const repoUrl = "https://github.com/smart-social-contracts/kybra-simple-token";
</script>

<div class="app-container">
  <slot />
  
  <footer class="app-footer">
    <div class="footer-row ic-branding">
      <img src="/internet-computer-icp-logo.svg" alt="Internet Computer" width="24" height="24" />
      <span>Built on the Internet Computer</span>
    </div>
    
    <a href={repoUrl} target="_blank" rel="noopener noreferrer" class="footer-row github-link">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
      </svg>
    </a>
    
    <div class="footer-row version-info">
      NFT Collection {version} ({commitHash}) - {buildTime}
    </div>
  </footer>
</div>

<style>
  .app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .app-footer {
    margin-top: auto;
    padding: 24px;
    text-align: center;
    border-top: 1px solid var(--color-border);
    background: var(--color-bg-secondary);
  }

  .footer-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 12px;
  }

  .footer-row:last-child {
    margin-bottom: 0;
  }

  .ic-branding {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .github-link {
    color: var(--color-text-tertiary);
    text-decoration: none;
    transition: color 0.15s;
  }

  .github-link:hover {
    color: var(--color-text-primary);
  }

  .version-info {
    color: var(--color-text-tertiary);
    font-size: 0.75rem;
    font-family: monospace;
  }
</style>
