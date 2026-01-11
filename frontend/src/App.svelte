<script>
  import { onMount } from 'svelte';
  import { executeQuery, fetchSchema } from './api.js';
  import QueryInput from './lib/QueryInput.svelte';
  import SqlDisplay from './lib/SqlDisplay.svelte';
  import ResultsTable from './lib/ResultsTable.svelte';
  import ErrorMessage from './lib/ErrorMessage.svelte';

  let query = $state('');
  let loading = $state(false);
  let result = $state(null);
  let error = $state(null);
  let schemaInfo = $state(null);
  let schemaError = $state(null);

  const exampleQueries = [
    'Average tip by payment type',
    'Total fares in the last 24 hours',
    'Count trips by pickup location',
    'Trips over 2 hours in the last year',
  ];

  onMount(async () => {
    try {
      const response = await fetchSchema();
      schemaInfo = response.schema || null;
    } catch (err) {
      schemaError = err.message || 'Failed to load dataset info';
    }
  });

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

  function applyExample(example) {
    query = example;
  }

</script>

<main>
  <header>
    <h1>NL → ClickHouse SQL</h1>
    <p>Ask questions in natural language, get SQL and results</p>
  </header>

  <section class="input-section">
    <QueryInput bind:query {loading} onSubmit={handleSubmit} />
    <div class="examples">
      <span class="label">Try:</span>
      {#each exampleQueries as example}
        <button type="button" class="example" onclick={() => applyExample(example)}>
          {example}
        </button>
      {/each}
    </div>
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

  <section class="schema-section">
    <h2>Dataset Info</h2>
    {#if schemaError}
      <div class="schema-error">{schemaError}</div>
    {:else if schemaInfo}
      <details>
        <summary>Show schema</summary>
        <pre><code>{schemaInfo}</code></pre>
      </details>
    {:else}
      <div class="schema-loading">Loading schema...</div>
    {/if}
  </section>

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

  .examples {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .examples .label {
    font-size: 0.85rem;
    color: #666;
    align-self: center;
  }

  .example {
    border: 1px solid #dbeafe;
    background: #eff6ff;
    color: #1e3a8a;
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .example:hover {
    background: #dbeafe;
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

  .schema-section {
    margin-top: 2rem;
    padding: 1.25rem;
    border-radius: 8px;
    background: #fff7ed;
    border: 1px solid #fed7aa;
  }

  .schema-section h2 {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    color: #9a3412;
  }

  .schema-section summary {
    cursor: pointer;
    color: #9a3412;
  }

  .schema-section pre {
    margin: 0.75rem 0 0 0;
    padding: 0.75rem;
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 6px;
    font-size: 0.75rem;
    overflow-x: auto;
  }

  .schema-loading {
    color: #9a3412;
    font-size: 0.85rem;
  }

  .schema-error {
    color: #b91c1c;
    background: #fee2e2;
    padding: 0.5rem;
    border-radius: 6px;
    font-size: 0.85rem;
  }

</style>
