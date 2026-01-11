<script>
  import { executeQuery } from './api.js';
  import QueryInput from './lib/QueryInput.svelte';
  import SqlDisplay from './lib/SqlDisplay.svelte';
  import ResultsTable from './lib/ResultsTable.svelte';
  import ErrorMessage from './lib/ErrorMessage.svelte';

  let query = $state('');
  let loading = $state(false);
  let result = $state(null);
  let error = $state(null);

  async function handleSubmit() {
    loading = true;
    error = null;
    result = null;

    try {
      const response = await executeQuery(query);

      if (response.success === false) {
        error = response.error || 'Query failed';
        if (response.sql) {
          result = { sql: response.sql, data: [], columns: [], row_count: 0, elapsed_ms: 0 };
        }
      } else {
        result = response;
      }
    } catch (err) {
      error = err.message || 'An unexpected error occurred';
    } finally {
      loading = false;
    }
  }

</script>

<main>
  <header>
    <h1>NL → ClickHouse SQL</h1>
    <p>Ask questions in natural language, get SQL and results</p>
  </header>

  <section class="input-section">
    <QueryInput bind:query {loading} onSubmit={handleSubmit} />
  </section>

  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <span>Generating SQL and executing query...</span>
    </div>
  {/if}

  <ErrorMessage {error} />

  {#if result}
    <SqlDisplay sql={result.sql} />
    <ResultsTable
      data={result.data}
      columns={result.columns}
      rowCount={result.row_count}
      elapsedMs={result.elapsed_ms}
    />
  {/if}

</main>

<style>
  main {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
  }

  header {
    margin-bottom: 2rem;
  }

  h1 {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
    color: #111;
  }

  header p {
    margin: 0.5rem 0 0 0;
    color: #666;
  }

  .input-section {
    background: #fff;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .loading {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding: 1rem;
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 6px;
    color: #0369a1;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #bae6fd;
    border-top-color: #0369a1;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

</style>
