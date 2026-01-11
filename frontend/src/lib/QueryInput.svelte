<script>
  let { query = $bindable(""), onSubmit, loading = false } = $props();

  function handleSubmit() {
    if (query.trim() && !loading) {
      onSubmit();
    }
  }

  function handleKeydown(event) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      handleSubmit();
    }
  }
</script>

<div class="query-input">
  <textarea
    bind:value={query}
    placeholder="Enter your question... (e.g., 'How many taxi trips in the last 24 hours?')"
    rows="3"
    disabled={loading}
    onkeydown={handleKeydown}
  ></textarea>
  <button onclick={handleSubmit} disabled={loading || !query.trim()}>
    {#if loading}
      Running...
    {:else}
      Run Query
    {/if}
  </button>
  <span class="hint">Ctrl+Enter to run</span>
</div>

<style>
  .query-input {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  textarea {
    width: 100%;
    padding: 0.75rem;
    font-size: 1rem;
    font-family: inherit;
    border: 1px solid #ddd;
    border-radius: 6px;
    resize: vertical;
    min-height: 80px;
  }

  textarea:focus {
    outline: none;
    border-color: #0066cc;
    box-shadow: 0 0 0 2px rgba(0, 102, 204, 0.2);
  }

  textarea:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }

  button {
    align-self: flex-start;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    font-weight: 500;
    color: white;
    background: #0066cc;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
  }

  button:hover:not(:disabled) {
    background: #0052a3;
  }

  button:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  .hint {
    font-size: 0.8rem;
    color: #888;
  }
</style>
