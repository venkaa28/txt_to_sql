<script>
  let { data = [], columns = [], rowCount = 0, elapsedMs = 0 } = $props();
</script>

{#if columns.length > 0}
  <div class="results-table">
    <h3>
      Results
      <span class="meta"
        >({rowCount} row{rowCount !== 1 ? "s" : ""}, {elapsedMs.toFixed(
          1
        )}ms)</span
      >
    </h3>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            {#each columns as col}
              <th>{col}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each data as row}
            <tr>
              {#each columns as col}
                <td>{row[col] ?? ""}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
{/if}

<style>
  .results-table {
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

  .meta {
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    color: #888;
  }

  .table-wrapper {
    overflow-x: auto;
    border: 1px solid #ddd;
    border-radius: 6px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }

  th,
  td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid #eee;
  }

  th {
    background: #f8f8f8;
    font-weight: 600;
    color: #333;
    position: sticky;
    top: 0;
  }

  tr:last-child td {
    border-bottom: none;
  }

  tr:hover td {
    background: #fafafa;
  }

  td {
    font-family: "SF Mono", Monaco, "Cascadia Code", "Consolas", monospace;
    font-size: 0.85rem;
  }
</style>
