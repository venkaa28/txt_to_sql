<script>
  let { sql } = $props();
</script>

{#if sql}
  <div class="sql-display">
    <h3>Generated SQL</h3>
    <pre><code>{sql}</code></pre>
  </div>
{/if}

<style>
  .sql-display {
    margin-top: 1.5rem;
  }

  h3 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    font-weight: 600;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  pre {
    margin: 0;
    padding: 1rem;
    background: #1e1e1e;
    border-radius: 6px;
    overflow-x: auto;
  }

  code {
    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Consolas', monospace;
    font-size: 0.9rem;
    color: #d4d4d4;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
