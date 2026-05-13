<script>
  // Array of {url, source_name, sample_rank, ...} or null (loading) or [] (empty)
  export let articles = null;
  export let loading = false;
</script>

<div class="article-wrap" role="presentation" on:click|stopPropagation>
  {#if loading}
    <p class="status loading-msg">Loading articles…</p>
  {:else if articles === null}
    <p class="status prompt">Select a theme above to see sample articles</p>
  {:else if articles.length === 0}
    <p class="status empty">No sample articles available for this combination</p>
  {:else}
    <ul class="article-list">
      {#each articles as art}
        <li>
          <a
            href={art.url}
            target="_blank"
            rel="noopener noreferrer"
            class="article-link"
          >{art.source_name}</a>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .article-wrap {
    margin-top: 14px;
  }

  .status {
    font-family: var(--sans);
    font-size: 12.5px;
    color: #999;
    margin: 0;
  }

  .loading-msg {
    opacity: 0.7;
    font-style: italic;
  }

  .article-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .article-link {
    font-family: var(--sans);
    font-size: 13px;
    color: #1a3a6b;
    text-decoration: none;
  }

  .article-link:hover {
    text-decoration: underline;
  }
</style>
