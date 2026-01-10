<script>
  let { error } = $props();
</script>

{#if error}
  <div class="error-message">
    <span class="icon">⚠</span>
    <span class="text">{error}</span>
  </div>
{/if}

<style>
  .error-message {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding: 1rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 6px;
    color: #b91c1c;
  }

  .icon {
    flex-shrink: 0;
    font-size: 1.1rem;
  }

  .text {
    font-size: 0.95rem;
    line-height: 1.5;
  }
</style>
